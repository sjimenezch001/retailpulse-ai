"""Offline IAM documents for owner-managed foundations and one synthetic run.

Generation never creates a session or changes AWS. Every operator document,
including all guardrail shards, is mandatory as a single reviewed set.
"""

import json
from collections import defaultdict

from cloud.aws.contracts import LabError, canonical, digest

VERSION = "2012-10-17"
INLINE_POLICY = "bounded-etl"


def policy(statements):
    return {"Version": VERSION, "Statement": statements}


def statement(sid, actions, resources, *, effect="Allow", condition=None):
    result = {"Sid": sid, "Effect": effect, "Action": actions, "Resource": resources}
    if condition:
        result["Condition"] = condition
    return result


def trust_policy(settings):
    return policy(
        [
            {
                "Effect": "Allow",
                "Principal": {"Service": "glue.amazonaws.com"},
                "Action": "sts:AssumeRole",
                "Condition": {
                    "StringEquals": {"aws:SourceAccount": settings.account},
                    "ArnLike": {
                        "aws:SourceArn": settings.arn("glue", "*"),
                    },
                },
            }
        ]
    )


def bucket_policy(settings):
    bucket = f"arn:aws:s3:::{settings.bucket}"
    statements = [
        {
            "Sid": "DenyInsecureTransport",
            "Effect": "Deny",
            "Principal": "*",
            "Action": "s3:*",
            "Resource": [bucket, bucket + "/*"],
            "Condition": {"Bool": {"aws:SecureTransport": "false"}},
        },
        {
            "Sid": "DenyExplicitNonSseS3",
            "Effect": "Deny",
            "Principal": "*",
            "Action": "s3:PutObject",
            "Resource": [bucket + "/*"],
            "Condition": {
                "StringNotEquals": {"s3:x-amz-server-side-encryption": "AES256"},
                "Null": {"s3:x-amz-server-side-encryption": "false"},
            },
        },
        {
            "Sid": "DenyCustomerProvidedEncryption",
            "Effect": "Deny",
            "Principal": "*",
            "Action": "s3:PutObject",
            "Resource": [bucket + "/*"],
            "Condition": {
                "Null": {"s3:x-amz-server-side-encryption-customer-algorithm": "false"}
            },
        },
    ]
    # Absent encryption headers are intentional: Spark multipart uploads rely
    # on the independently verified AES256 bucket default.
    return policy(statements)


def bucket_configuration():
    return {
        "public_access_block": {
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        },
        "encryption": {
            "Rules": [
                {"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}
            ]
        },
        "ownership": {"Rules": [{"ObjectOwnership": "BucketOwnerEnforced"}]},
        "versioning": {"Status": "Enabled"},
        "lifecycle": {
            "Rules": [
                {
                    "ID": "temporary-results",
                    "Status": "Enabled",
                    "Filter": {"Prefix": "results/"},
                    "Expiration": {"Days": 1},
                },
                {
                    "ID": "bounded-lab-retention",
                    "Status": "Enabled",
                    "Filter": {},
                    "Expiration": {"Days": 7},
                    "NoncurrentVersionExpiration": {"NoncurrentDays": 1},
                    "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 1},
                },
            ]
        },
    }


def execution_policy(settings):
    bucket = f"arn:aws:s3:::{settings.bucket}"
    run = settings.run_id
    logs = [
        settings.arn(
            "logs", f"log-group:/retailpulse/{settings.environment}/glue/{kind}"
        )
        + ":log-stream:*"
        for kind in ("error", "output")
    ]
    groups = [
        (
            ["s3:GetObject"],
            [
                f"{bucket}/{category}/{run}/*"
                for category in ("input", "scripts", "curated", "temporary")
            ],
        ),
        (
            [
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:AbortMultipartUpload",
                "s3:ListMultipartUploadParts",
            ],
            [f"{bucket}/{category}/{run}/*" for category in ("curated", "temporary")],
        ),
        (["s3:ListBucket", "s3:GetBucketLocation"], [bucket]),
        (["logs:CreateLogStream", "logs:PutLogEvents"], logs),
    ]
    return policy(
        [
            statement(
                f"Execution{index}",
                actions,
                resources,
                condition={"StringEquals": {"s3:ResourceAccount": settings.account}}
                if actions[0].startswith("s3:")
                else None,
            )
            for index, (actions, resources) in enumerate(groups, 1)
        ]
    )


def execution_boundary(settings):
    grants = execution_policy(settings)["Statement"]
    actions = sorted({a for s in grants for a in s["Action"]})
    statements = [
        {
            "Sid": "ExplicitlyDenyEveryOtherAction",
            "Effect": "Deny",
            "NotAction": actions,
            "Resource": "*",
        },
        *grants,
    ]
    for index, grant in enumerate(grants, 1):
        statements.append(
            {
                "Sid": f"DenyOutsideExecutionScope{index}",
                "Effect": "Deny",
                "Action": grant["Action"],
                "NotResource": grant["Resource"],
            }
        )
    statements.append(
        statement(
            "DenyWrongS3Owner",
            [a for a in actions if a.startswith("s3:")],
            ["*"],
            effect="Deny",
            condition={"StringNotEquals": {"s3:ResourceAccount": settings.account}},
        )
    )
    return policy(statements)


def operator_policies(settings):
    bucket = f"arn:aws:s3:::{settings.bucket}"
    role = settings.glue_role_arn
    job = settings.arn("glue", "job/" + settings.name)
    catalog = settings.arn("glue", "catalog")
    database = settings.arn("glue", "database/" + settings.database)
    tables = [
        settings.arn("glue", f"table/{settings.database}/{name}")
        for name in (
            "mart_sales_daily",
            "dim_store",
            "dim_product",
            "pipeline_metadata",
            "store_units",
        )
    ]
    wg = settings.arn("athena", "workgroup/" + settings.name)
    logs = [
        settings.arn(
            "logs", f"log-group:/retailpulse/{settings.environment}/glue/{kind}"
        )
        for kind in ("error", "output")
    ]

    def scope(extra=None, regional=True):
        equal = {
            "aws:PrincipalArn": settings.operator_arn,
            "aws:PrincipalAccount": settings.account,
        }
        if regional:
            equal["aws:RequestedRegion"] = settings.region
        equal.update(extra or {})
        return {"StringEquals": equal}

    data_condition = scope({"s3:ResourceAccount": settings.account})
    uploads = [
        f"{bucket}/input/{settings.run_id}/{name}"
        for name in (
            "manifest.json",
            "mart_sales_daily.csv",
            "dim_store.csv",
            "dim_product.csv",
            "pipeline_metadata.csv",
        )
    ] + [
        f"{bucket}/scripts/{settings.run_id}/{name}"
        for name in ("glue_job.py", "glue_bundle.zip")
    ]
    uploads += [
        f"{bucket}/serving/{settings.run_id}/units.json",
        f"{bucket}/results/*",
    ]
    cleanup = [
        f"{bucket}/{category}/{settings.run_id}/*"
        for category in ("input", "scripts", "curated", "temporary", "serving")
    ] + [f"{bucket}/results/*"]
    storage = [
        statement(
            "VerifyExistingBucket",
            [
                "s3:ListBucket",
                "s3:GetBucketLocation",
                "s3:GetBucketTagging",
                "s3:GetBucketWebsite",
                "s3:GetBucketPolicy",
                "s3:GetBucketPolicyStatus",
                "s3:GetBucketPublicAccessBlock",
                "s3:GetBucketOwnershipControls",
                "s3:GetEncryptionConfiguration",
                "s3:GetBucketVersioning",
                "s3:GetLifecycleConfiguration",
                "s3:ListBucketVersions",
                "s3:ListBucketMultipartUploads",
            ],
            [bucket],
            condition=data_condition,
        ),
        statement(
            "ReadOnlyRunOutputs",
            ["s3:GetObject"],
            [f"{bucket}/curated/{settings.run_id}/*", f"{bucket}/results/*"],
            condition=data_condition,
        ),
        statement(
            "UploadReviewedInputsAndPublishResults",
            ["s3:PutObject"],
            uploads,
            condition=data_condition,
        ),
        statement(
            "CleanOnlyThisRun",
            ["s3:DeleteObject", "s3:DeleteObjectVersion", "s3:AbortMultipartUpload"],
            cleanup,
            condition=data_condition,
        ),
    ]
    identity = [
        statement(
            "VerifyFixedExecutionRole",
            [
                "iam:GetRole",
                "iam:GetRolePolicy",
                "iam:ListRolePolicies",
                "iam:ListAttachedRolePolicies",
            ],
            [role],
            condition=scope(regional=False),
        ),
        statement(
            "VerifyImmutableBoundary",
            ["iam:GetPolicy", "iam:GetPolicyVersion"],
            [settings.glue_boundary_arn],
            condition=scope(regional=False),
        ),
        statement(
            "PassOnlyFixedGlueRole",
            ["iam:PassRole"],
            [role],
            condition=scope(
                {"iam:PassedToService": "glue.amazonaws.com"}, regional=False
            ),
        ),
    ]
    workloads = [
        statement(
            "ManageOnlyLabJob",
            [
                "glue:CreateJob",
                "glue:GetJob",
                "glue:UpdateJob",
                "glue:DeleteJob",
                "glue:GetTags",
                "glue:TagResource",
                "glue:UntagResource",
                "glue:StartJobRun",
                "glue:GetJobRun",
                "glue:GetJobRuns",
                "glue:BatchStopJobRun",
            ],
            [job],
            condition=scope(),
        ),
        statement(
            "ManageOnlyLabDatabase",
            ["glue:CreateDatabase", "glue:GetDatabase", "glue:UpdateDatabase"],
            [catalog, database],
            condition=scope(),
        ),
        statement(
            "ManageOnlyFiveTables",
            [
                "glue:CreateTable",
                "glue:GetTable",
                "glue:UpdateTable",
                "glue:DeleteTable",
            ],
            [catalog, database, *tables],
            condition=scope(),
        ),
        statement(
            "DeleteOnlyLabDatabase",
            ["glue:DeleteDatabase"],
            [
                catalog,
                database,
                settings.arn("glue", f"table/{settings.database}/*"),
                settings.arn("glue", f"userDefinedFunction/{settings.database}/*"),
            ],
            condition=scope(),
        ),
        statement(
            "TagOnlyLabDatabase",
            ["glue:GetTags", "glue:TagResource", "glue:UntagResource"],
            [database],
            condition=scope(),
        ),
        statement(
            "ManageOnlyLabWorkgroup",
            [
                "athena:CreateWorkGroup",
                "athena:GetWorkGroup",
                "athena:UpdateWorkGroup",
                "athena:DeleteWorkGroup",
                "athena:ListTagsForResource",
                "athena:TagResource",
                "athena:UntagResource",
                "athena:StartQueryExecution",
                "athena:GetQueryExecution",
                "athena:GetQueryResults",
                "athena:StopQueryExecution",
                "athena:ListQueryExecutions",
            ],
            [wg],
            condition=scope(),
        ),
        statement(
            "ManageOnlyTwoLogGroups",
            ["logs:CreateLogGroup", "logs:PutRetentionPolicy", "logs:DeleteLogGroup"],
            [name + ":*" for name in logs],
            condition=scope(),
        ),
        statement(
            "TagOnlyTwoLogGroups",
            ["logs:ListTagsForResource", "logs:TagResource", "logs:UntagResource"],
            logs,
            condition=scope(),
        ),
        statement(
            "ReadRegionalLogInventory",
            ["logs:DescribeLogGroups"],
            ["*"],
            condition=scope(),
        ),
    ]
    result = {
        "operator-storage.json": policy(storage),
        "operator-identity.json": policy(identity),
        "operator-workloads.json": policy(workloads),
    }
    grants = [*storage, *identity, *workloads]
    allowed = sorted({action for grant in grants for action in grant["Action"]})
    guards = [
        {
            "Sid": "DenyEveryOtherAction",
            "Effect": "Deny",
            "NotAction": [*allowed, "sts:GetCallerIdentity"],
            "Resource": "*",
        },
        statement(
            "DenyWrongPassRoleService",
            ["iam:PassRole"],
            [role],
            effect="Deny",
            condition={
                "StringNotEquals": {"iam:PassedToService": "glue.amazonaws.com"}
            },
        ),
        statement(
            "DenyWrongRegionalEndpoint",
            [a for a in allowed if not a.startswith("iam:")],
            ["*"],
            effect="Deny",
            condition={"StringNotEquals": {"aws:RequestedRegion": settings.region}},
        ),
        statement(
            "DenyWrongObjectOwner",
            [a for a in allowed if a.startswith("s3:")],
            ["*"],
            effect="Deny",
            condition={"StringNotEquals": {"s3:ResourceAccount": settings.account}},
        ),
    ]
    # Explicit resource denials protect against same-account resource-policy
    # grants directly to an assumed-role session, not just identity-policy Allows.
    resources_by_action = defaultdict(set)
    for grant in grants:
        for action in grant["Action"]:
            resources_by_action[action].update(grant["Resource"])
    actions_by_resources = defaultdict(list)
    for action, resources in resources_by_action.items():
        if "*" not in resources:
            actions_by_resources[tuple(sorted(resources))].append(action)
    for index, (resources, actions) in enumerate(actions_by_resources.items(), 1):
        guards.append(
            {
                "Sid": f"DenyOutsideReviewedResources{index}",
                "Effect": "Deny",
                "Action": sorted(actions),
                "NotResource": list(resources),
            }
        )
    # Split mandatory custom managed policies instead of silently exceeding IAM quotas.
    shard = []
    number = 1
    for guard in guards:
        if len(canonical(policy([*shard, guard]))) > 6000:
            result[f"operator-guardrails-{number}.json"] = policy(shard)
            shard, number = [], number + 1
        shard.append(guard)
    result[f"operator-guardrails-{number}.json"] = policy(shard)
    if any(len(canonical(value)) > 6144 for value in result.values()):
        raise LabError("operator_policy_quota")
    return result


def review_bundle(settings):
    documents = {
        "glue-trust.json": trust_policy(settings),
        "glue-execution.json": execution_policy(settings),
        "glue-boundary.json": execution_boundary(settings),
        "bucket-policy.json": bucket_policy(settings),
        "bucket-settings.json": bucket_configuration(),
        **operator_policies(settings),
    }
    return {
        "status": "OFFLINE PROPOSAL; OWNER BOOTSTRAP PENDING; AWS LIVE PENDING",
        "account": settings.account,
        "region": settings.region,
        "environment": settings.environment,
        "run_id": settings.run_id,
        "bucket": settings.bucket,
        "role_arn": settings.glue_role_arn,
        "boundary_arn": settings.glue_boundary_arn,
        "operator_arn": settings.operator_arn,
        "tags": settings.tags,
        "documents": documents,
        "sha256": {name: digest(canonical(value)) for name, value in documents.items()},
    }


def write_bundle(settings, destination):
    destination.mkdir(parents=True, exist_ok=True)
    result = review_bundle(settings)
    for name, document in result["documents"].items():
        (destination / name).write_text(
            json.dumps(document, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
    (destination / "review.json").write_text(
        json.dumps({k: v for k, v in result.items() if k != "documents"}, indent=2)
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return result
