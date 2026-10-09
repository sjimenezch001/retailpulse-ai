"""RP-12C adversarial offline tests. IAM model is limited, not an AWS simulator."""

import copy
import fnmatch
import json

import pytest
from cloud.aws.contracts import LabError
from cloud.aws.foundations import verify_foundations
from cloud.aws.ownership import empty_owned_bucket, verify_state
from cloud.aws.policies import (
    bucket_policy,
    execution_boundary,
    operator_policies,
    review_bundle,
)


def sequence(value):
    return value if isinstance(value, list) else [value]


def decision(statements, action, resource, context):
    allowed = False
    for statement in statements:
        applies = any(
            fnmatch.fnmatchcase(action.lower(), pattern.lower())
            for pattern in sequence(statement.get("Action", statement.get("NotAction")))
        )
        if "NotAction" in statement:
            applies = not applies
        if not applies:
            continue
        applies = any(
            fnmatch.fnmatchcase(resource, pattern)
            for pattern in sequence(
                statement.get("Resource", statement.get("NotResource"))
            )
        )
        if "NotResource" in statement:
            applies = not applies
        if not applies:
            continue
        conditions_match = True
        for operator, terms in statement.get("Condition", {}).items():
            for key, expected in terms.items():
                present = key in context
                if operator == "StringEquals":
                    ok = present and context[key] in sequence(expected)
                elif operator == "StringNotEquals":
                    ok = not present or context[key] not in sequence(expected)
                elif operator == "Null":
                    ok = (not present) == (str(expected).lower() == "true")
                elif operator == "Bool":
                    ok = present and str(context[key]).lower() == str(expected).lower()
                else:
                    raise AssertionError("Unsupported test condition")
                conditions_match &= ok
        if not conditions_match:
            continue
        if statement["Effect"] == "Deny":
            return "Deny"
        allowed = True
    return "Allow" if allowed else "Deny"


def operator_statements(settings):
    return [
        statement
        for policy in operator_policies(settings).values()
        for statement in policy["Statement"]
    ]


def context(settings):
    return {
        "aws:PrincipalArn": settings.operator_arn,
        "aws:PrincipalAccount": settings.account,
        "aws:RequestedRegion": settings.region,
        "s3:ResourceAccount": settings.account,
    }


@pytest.mark.parametrize(
    "action,resource",
    [
        ("iam:CreateRole", "role"),
        ("iam:PutRolePolicy", "role"),
        ("iam:UpdateAssumeRolePolicy", "role"),
        ("iam:PutRolePermissionsBoundary", "role"),
        ("iam:DeleteRolePermissionsBoundary", "role"),
        ("iam:AttachRolePolicy", "role"),
        ("iam:CreatePolicyVersion", "boundary"),
        ("s3:PutBucketPolicy", "bucket"),
        ("s3:PutBucketPublicAccessBlock", "bucket"),
        ("s3:PutEncryptionConfiguration", "bucket"),
        ("s3:DeleteBucket", "bucket"),
        ("glue:CreateSecurityConfiguration", "*"),
        ("logs:PutResourcePolicy", "*"),
        ("lambda:CreateFunction", "*"),
        ("apigateway:POST", "*"),
        ("redshift:CreateCluster", "*"),
        ("ec2:RunInstances", "*"),
        ("rds:CreateDBInstance", "*"),
    ],
)
def test_operator_cannot_mutate_foundations_or_deferred_services(
    settings, action, resource
):
    target = {
        "role": settings.glue_role_arn,
        "boundary": settings.glue_boundary_arn,
        "bucket": f"arn:aws:s3:::{settings.bucket}",
        "*": "*",
    }[resource]
    # An additional identity/resource-policy Allow must not evade the explicit guards.
    grants = operator_statements(settings) + [
        {"Effect": "Allow", "Action": "*", "Resource": "*"}
    ]
    assert decision(grants, action, target, context(settings)) == "Deny"


@pytest.mark.parametrize(
    "service", ["glue.amazonaws.com", "lambda.amazonaws.com", "ec2.amazonaws.com", None]
)
@pytest.mark.parametrize("correct_role", [True, False])
def test_exact_passrole_and_service_even_with_additional_allow(
    settings, service, correct_role
):
    grants = operator_statements(settings) + [
        {"Effect": "Allow", "Action": "iam:PassRole", "Resource": "*"}
    ]
    ctx = context(settings)
    if service is not None:
        ctx["iam:PassedToService"] = service
    role = settings.glue_role_arn if correct_role else settings.operator_arn
    expected = "Allow" if correct_role and service == "glue.amazonaws.com" else "Deny"
    assert decision(grants, "iam:PassRole", role, ctx) == expected


@pytest.mark.parametrize(
    "action,resource",
    [
        ("s3:GetObject", "arn:aws:s3:::another-bucket/secret"),
        ("s3:PutObject", "arn:aws:s3:::another-bucket/input"),
        ("glue:StartJobRun", "arn:aws:glue:sa-east-1:000000000000:job/other"),
        (
            "athena:StartQueryExecution",
            "arn:aws:athena:sa-east-1:000000000000:workgroup/other",
        ),
        ("iam:GetRole", "arn:aws:iam::000000000000:role/other"),
    ],
)
def test_other_resources_remain_denied_with_resource_policy_grant(
    settings, action, resource
):
    grants = operator_statements(settings) + [
        {"Effect": "Allow", "Action": action, "Resource": resource}
    ]
    assert decision(grants, action, resource, context(settings)) == "Deny"


def test_current_run_upload_allowed_but_old_run_and_curated_writes_denied(settings):
    statements = operator_statements(settings)
    base = f"arn:aws:s3:::{settings.bucket}/"
    ctx = context(settings)
    assert (
        decision(
            statements,
            "s3:PutObject",
            base + settings.key("input", "manifest.json"),
            ctx,
        )
        == "Allow"
    )
    for key in [
        f"input/{'f' * 24}/manifest.json",
        settings.key("curated", "forged.parquet"),
    ]:
        assert decision(statements, "s3:PutObject", base + key, ctx) == "Deny"


def test_only_read_only_regional_wildcard_and_managed_policy_quotas(settings):
    for name, value in operator_policies(settings).items():
        assert len(json.dumps(value, separators=(",", ":"))) <= 6144
        for statement in value["Statement"]:
            if statement["Effect"] != "Allow":
                continue
            assert all("*" not in a for a in statement["Action"])
            if "*" in statement["Resource"]:
                assert statement["Action"] == ["logs:DescribeLogGroups"]
                assert (
                    statement["Condition"]["StringEquals"]["aws:RequestedRegion"]
                    == settings.region
                )


@pytest.mark.parametrize(
    "kind",
    [
        "aws_s3_bucket",
        "aws_iam_role",
        "aws_iam_role_policy",
        "aws_s3_bucket_policy",
        "aws_glue_security_configuration",
        "aws_lambda_function",
    ],
)
def test_legacy_managed_foundations_or_endpoint_cannot_be_destroyed(
    settings, outputs, kind
):
    state = {
        "values": {
            "root_module": {
                "resources": [
                    {
                        "mode": "managed",
                        "type": kind,
                        "values": {
                            "name": settings.name,
                            "id": settings.name,
                            "bucket": settings.bucket,
                        },
                    }
                ]
            }
        }
    }
    with pytest.raises(LabError, match="owner_managed"):
        verify_state(state, settings, outputs)


def test_read_only_foundation_references_and_workload_state(settings, outputs):
    state = {
        "values": {
            "root_module": {
                "resources": [
                    {
                        "mode": "data",
                        "type": "aws_s3_bucket",
                        "values": {
                            "bucket": settings.bucket,
                            "arn": f"arn:aws:s3:::{settings.bucket}",
                        },
                    },
                    {
                        "mode": "data",
                        "type": "aws_iam_role",
                        "values": {"arn": settings.glue_role_arn},
                    },
                    {
                        "mode": "managed",
                        "type": "aws_glue_job",
                        "values": {
                            "name": settings.name,
                            "id": settings.name,
                            "tags": settings.tags,
                        },
                    },
                ]
            }
        }
    }
    assert verify_state(state, settings, outputs)
    state["values"]["root_module"]["resources"][1]["values"]["arn"] = (
        settings.operator_arn
    )
    with pytest.raises(LabError, match="foreign"):
        verify_state(state, settings, outputs)


def test_foundations_verified_using_only_reads(foundations, settings):
    result = verify_foundations(foundations, settings)
    assert result["owner_foundations_verified"] and result["run_id"] == settings.run_id


@pytest.mark.parametrize(
    "fault",
    [
        "public",
        "encryption",
        "tls",
        "ownership",
        "versioning",
        "lifecycle",
        "trust",
        "boundary",
        "inline",
        "attached",
        "role",
    ],
)
def test_untrusted_foundation_fails_closed_before_any_upload(
    foundations, settings, fault
):
    s3, iam = foundations["s3"], foundations["iam"]
    if fault == "public":
        s3.security["public_access_block"]["BlockPublicPolicy"] = False
    elif fault == "encryption":
        s3.security["encryption"]["Rules"][0]["ApplyServerSideEncryptionByDefault"][
            "SSEAlgorithm"
        ] = "aws:kms"
    elif fault == "tls":
        s3.policy["Statement"][0]["Effect"] = "Allow"
    elif fault == "ownership":
        s3.security["ownership"]["Rules"][0]["ObjectOwnership"] = "ObjectWriter"
    elif fault == "versioning":
        s3.security["versioning"]["Status"] = "Suspended"
    elif fault == "lifecycle":
        s3.security["lifecycle"]["Rules"] = []
    elif fault == "trust":
        iam.role["AssumeRolePolicyDocument"]["Statement"][0].pop("Condition")
    elif fault == "boundary":
        iam.boundary["Statement"] = []
    elif fault == "inline":
        iam.inline["Statement"][0]["Resource"] = ["*"]
    elif fault == "attached":
        iam.attached = [{"PolicyArn": "arn:aws:iam::aws:policy/AdministratorAccess"}]
    else:
        iam.role["Arn"] = settings.operator_arn
    with pytest.raises(LabError):
        verify_foundations(foundations, settings)
    assert not s3.writes and not s3.deletes


def test_unsafe_bucket_blocks_cleanup_without_mutating_any_object(s3, settings):
    s3.policy = {"Version": "2012-10-17", "Statement": []}
    with pytest.raises(LabError, match="bucket_tls"):
        empty_owned_bucket(s3, settings)
    assert not s3.deletes and not s3.aborts


def test_old_run_objects_stop_cleanup_before_any_mutation(s3, settings):
    s3.versions = [{"Key": f"input/{'f' * 24}/manifest.json", "VersionId": "old"}]
    with pytest.raises(LabError, match="unexpected_object"):
        empty_owned_bucket(s3, settings)
    assert not s3.deletes and not s3.aborts


def test_sse_s3_default_accepts_absent_headers_but_rejects_alternatives(settings):
    policy = bucket_policy(settings)["Statement"]
    resource = f"arn:aws:s3:::{settings.bucket}/temporary/{settings.run_id}/part"
    # A hypothetical identity grant makes policy Deny behavior observable.
    grants = policy + [
        {"Effect": "Allow", "Action": "s3:PutObject", "Resource": resource}
    ]
    assert (
        decision(grants, "s3:PutObject", resource, {"aws:SecureTransport": True})
        == "Allow"
    )
    for ctx in [
        {"aws:SecureTransport": False},
        {"aws:SecureTransport": True, "s3:x-amz-server-side-encryption": "aws:kms"},
        {
            "aws:SecureTransport": True,
            "s3:x-amz-server-side-encryption-customer-algorithm": "AES256",
        },
    ]:
        assert decision(grants, "s3:PutObject", resource, ctx) == "Deny"


def test_execution_boundary_explicitly_limits_session_resource_grants(settings):
    statements = execution_boundary(settings)["Statement"]
    statements.append({"Effect": "Allow", "Action": "*", "Resource": "*"})
    assert (
        decision(statements, "iam:PassRole", settings.glue_role_arn, context(settings))
        == "Deny"
    )
    assert (
        decision(
            statements, "s3:GetObject", "arn:aws:s3:::other/secret", context(settings)
        )
        == "Deny"
    )


def test_bundle_generation_is_offline_and_bound_to_run(settings):
    bundle = review_bundle(settings)
    assert bundle["run_id"] == settings.run_id
    other = copy.copy(settings)
    object.__setattr__(other, "run_id", "f" * 24)
    assert (
        review_bundle(other)["sha256"]["glue-execution.json"]
        != bundle["sha256"]["glue-execution.json"]
    )


def test_terraform_has_no_managed_foundation_or_endpoint_blocks(root):
    import re

    text = "\n".join(
        p.read_text(encoding="utf-8") for p in (root / "infra/aws").glob("*.tf")
    )
    managed = re.findall(r'resource\s+"([^"]+)"', text)
    assert set(managed) == {
        "aws_glue_job",
        "aws_glue_catalog_database",
        "aws_glue_catalog_table",
        "aws_athena_workgroup",
        "aws_cloudwatch_log_group",
    }
    assert "security_configuration" not in text


def test_endpoint_flag_is_rejected_before_authentication(monkeypatch, capsys):
    from scripts import aws_lab

    def forbidden(*args):
        pytest.fail("Deferred endpoint must fail before authentication")

    monkeypatch.setattr(aws_lab, "authenticated_session", forbidden)
    assert aws_lab.main(["prepare", "--enable-endpoint"]) == 1
    assert "endpoint_deferred" in capsys.readouterr().out


def test_workload_teardown_preserves_owner_foundations(
    monkeypatch, tmp_path, settings, outputs, foundations
):
    from types import SimpleNamespace

    from cloud.aws import operations

    class Absent(Exception):
        def __init__(self, code):
            self.response = {"Error": {"Code": code, "Message": "resource not found"}}

    def absent(code):
        def call(**kwargs):
            raise Absent(code)

        return call

    clients = {
        **foundations,
        "glue": SimpleNamespace(
            get_job=absent("EntityNotFoundException"),
            get_database=absent("EntityNotFoundException"),
        ),
        "athena": SimpleNamespace(get_work_group=absent("InvalidRequestException")),
        "logs": SimpleNamespace(describe_log_groups=lambda **kwargs: {"logGroups": []}),
    }
    runner = operations.Operations.__new__(operations.Operations)
    runner.settings, runner.clients = settings, clients
    runner.directory = tmp_path
    runner.state = tmp_path / "terraform.tfstate"
    runner.state.write_text("stub recovery state")
    runner.variables = tmp_path / "lab.tfvars.json"
    runner.outputs = lambda: outputs
    calls = []

    def tf(*args, capture=False):
        calls.append(args)
        return ""

    runner.tf = tf
    monkeypatch.setattr(operations, "verify_resources", lambda *args: None)
    monkeypatch.setattr(
        operations,
        "stop_workloads",
        lambda *args, **kwargs: {"stopped_job_runs": 0, "stopped_queries": 0},
    )
    result = runner.teardown()
    assert result["complete"] is True
    assert result["owner_foundations_preserved"]["owner_foundations_verified"]
    assert result["owner_cleanup"].startswith("PENDING")
    assert calls[0][0] == "destroy"
    assert verify_foundations(clients, settings)["owner_foundations_verified"]
