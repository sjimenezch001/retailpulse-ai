"""Fail-closed read-only verification of owner-controlled AWS foundations."""

import json
from urllib.parse import unquote

from cloud.aws.contracts import LabError, canonical, digest
from cloud.aws.policies import (
    INLINE_POLICY,
    bucket_configuration,
    bucket_policy,
    execution_boundary,
    execution_policy,
    trust_policy,
)


def document(value):
    if isinstance(value, str):
        try:
            value = json.loads(unquote(value))
        except (ValueError, TypeError) as exc:
            raise LabError("foundation_policy_invalid") from exc
    if not isinstance(value, dict):
        raise LabError("foundation_policy_invalid")
    return value


def verify_bucket_security(s3, settings):
    args = {"Bucket": settings.bucket, "ExpectedBucketOwner": settings.account}
    expected = bucket_configuration()
    actual = s3.get_public_access_block(**args)["PublicAccessBlockConfiguration"]
    if actual != expected["public_access_block"]:
        raise LabError("bucket_public_access_block_incompatible")
    encryption = s3.get_bucket_encryption(**args)["ServerSideEncryptionConfiguration"]
    rules = encryption.get("Rules", [])
    if len(rules) != 1 or rules[0].get("ApplyServerSideEncryptionByDefault") != {
        "SSEAlgorithm": "AES256"
    }:
        raise LabError("bucket_sse_s3_required")
    ownership = s3.get_bucket_ownership_controls(**args)["OwnershipControls"]
    if ownership != expected["ownership"]:
        raise LabError("bucket_acl_ownership_incompatible")
    if s3.get_bucket_versioning(**args).get("Status") != "Enabled":
        raise LabError("bucket_versioning_required")
    lifecycle = s3.get_bucket_lifecycle_configuration(**args).get("Rules", [])
    if sorted(lifecycle, key=lambda r: r["ID"]) != sorted(
        expected["lifecycle"]["Rules"], key=lambda r: r["ID"]
    ):
        raise LabError("bucket_lifecycle_incompatible")
    actual_policy = document(s3.get_bucket_policy(**args)["Policy"])
    if actual_policy != bucket_policy(settings):
        raise LabError("bucket_tls_or_encryption_policy_incompatible")
    if s3.get_bucket_policy_status(**args)["PolicyStatus"].get("IsPublic") is not False:
        raise LabError("bucket_public_policy_rejected")
    return digest(canonical(actual_policy))


def verify_foundations(clients, settings):
    # Imported lazily to avoid a module cycle: bucket identity and tags are also
    # checked by destructive object cleanup, independently of role metadata.
    from cloud.aws.ownership import verify_bucket

    verify_bucket(clients["s3"], settings)
    bucket_hash = verify_bucket_security(clients["s3"], settings)
    iam = clients["iam"]
    role = iam.get_role(RoleName=settings.name + "-glue")["Role"]
    if role.get("Arn") != settings.glue_role_arn or role.get("Path") != "/":
        raise LabError("owner_glue_role_identity")
    if role.get("PermissionsBoundary", {}).get("PermissionsBoundaryArn") != (
        settings.glue_boundary_arn
    ):
        raise LabError("owner_glue_boundary_required")
    if document(role.get("AssumeRolePolicyDocument")) != trust_policy(settings):
        raise LabError("owner_glue_trust_incompatible")
    tags = {tag["Key"]: tag["Value"] for tag in role.get("Tags", [])}
    if any(tags.get(k) != v for k, v in settings.tags.items()):
        raise LabError("owner_glue_role_tags")
    names = iam.list_role_policies(RoleName=settings.name + "-glue")
    attached = iam.list_attached_role_policies(RoleName=settings.name + "-glue")
    if (
        names.get("IsTruncated")
        or names.get("PolicyNames") != [INLINE_POLICY]
        or attached.get("IsTruncated")
        or attached.get("AttachedPolicies") != []
    ):
        raise LabError("owner_glue_policy_inventory")
    inline = document(
        iam.get_role_policy(RoleName=settings.name + "-glue", PolicyName=INLINE_POLICY)[
            "PolicyDocument"
        ]
    )
    if inline != execution_policy(settings):
        raise LabError("owner_glue_execution_policy_incompatible_or_stale")
    boundary = iam.get_policy(PolicyArn=settings.glue_boundary_arn)["Policy"]
    if boundary.get("Arn") != settings.glue_boundary_arn:
        raise LabError("owner_glue_boundary_identity")
    version = iam.get_policy_version(
        PolicyArn=settings.glue_boundary_arn,
        VersionId=boundary["DefaultVersionId"],
    )["PolicyVersion"]
    if version.get("IsDefaultVersion") is not True or document(
        version["Document"]
    ) != execution_boundary(settings):
        raise LabError("owner_glue_boundary_incompatible_or_stale")
    return {
        "owner_foundations_verified": True,
        "run_id": settings.run_id,
        "bucket_policy_sha256": bucket_hash,
        "trust_sha256": digest(canonical(trust_policy(settings))),
        "execution_sha256": digest(canonical(inline)),
        "boundary_sha256": digest(canonical(execution_boundary(settings))),
        "owner_managed_cleanup": "PENDING; manual owner task after workload teardown",
    }
