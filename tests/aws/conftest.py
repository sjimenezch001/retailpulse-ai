"""Offline AWS tests forbid socket connections and credential discovery."""

import copy
import io
import socket
from pathlib import Path

import pytest
from cloud.aws.analytics import reference_queries
from cloud.aws.contracts import metric_reference, packaged_inputs
from cloud.aws.settings import Settings

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def no_network(monkeypatch, tmp_path):
    def deny(*args, **kwargs):
        raise AssertionError("A cloud unit test attempted a real network connection")

    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(socket, "getaddrinfo", deny)
    for name in (
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "AWS_PROFILE",
        "AWS_WEB_IDENTITY_TOKEN_FILE",
        "AWS_ROLE_ARN",
        "AWS_CONTAINER_CREDENTIALS_FULL_URI",
        "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI",
        "AWS_ENDPOINT_URL",
    ):
        monkeypatch.delenv(name, raising=False)
    empty = tmp_path / "empty-config"
    empty.write_text("")
    monkeypatch.setenv("AWS_CONFIG_FILE", str(empty))
    monkeypatch.setenv("AWS_SHARED_CREDENTIALS_FILE", str(empty))
    monkeypatch.setenv("AWS_EC2_METADATA_DISABLED", "true")


@pytest.fixture
def root():
    return ROOT


@pytest.fixture
def inputs():
    return packaged_inputs(ROOT)


@pytest.fixture
def settings():
    return Settings("000000000000", "sa-east-1", "offline", "0" * 24)


@pytest.fixture
def metric(inputs, settings):
    _, trusted, tables = inputs
    return metric_reference(tables, trusted, settings.run_id)


@pytest.fixture
def prepared(inputs, metric):
    return {"metric_reference": metric, "query_reference": reference_queries(inputs[2])}


@pytest.fixture
def reconciled(metric):
    result = copy.deepcopy(metric)
    result["reconciliation"] = {
        "engine": "athena",
        "checks": [
            "total_units",
            "by_store",
            "by_date",
            "dimension_join",
            "quality",
            "row_counts",
        ],
        "query_ids": [f"stub-query-{n}" for n in range(6)],
    }
    return result


@pytest.fixture
def outputs(settings):
    return {
        "account": settings.account,
        "region": settings.region,
        "environment": settings.environment,
        "lab_id": settings.lab_id,
        "run_id": settings.run_id,
        "bucket": settings.bucket,
        "database": settings.database,
        "job": settings.name,
        "workgroup": settings.name,
        "tags": settings.tags,
        "glue_role": settings.name + "-glue",
        "glue_role_arn": settings.glue_role_arn,
        "boundary_arn": settings.glue_boundary_arn,
        "owner_managed": ["bucket", "glue_role", "glue_boundary"],
        "lambda_role": None,
        "function": None,
        "api_id": None,
        "endpoint": None,
        "log_groups": [
            f"/retailpulse/{settings.environment}/glue/error",
            f"/retailpulse/{settings.environment}/glue/output",
        ],
    }


class StubError(Exception):
    def __init__(self, code="AccessDenied"):
        self.response = {"Error": {"Code": code, "Message": "stub error"}}


@pytest.fixture
def s3(settings):
    class S3:
        def __init__(self):
            self.objects = {}
            self.writes = []
            self.deletes = []
            self.aborts = []
            self.versions = []
            self.uploads = []
            self.tags = settings.tags.copy()
            self.region = settings.region
            self.denied = False
            from cloud.aws.policies import bucket_configuration, bucket_policy

            self.security = bucket_configuration()
            self.policy = bucket_policy(settings)
            self.public = False

        def get_object(self, **args):
            if self.denied:
                raise StubError()
            if args["Key"] not in self.objects:
                raise StubError("NoSuchKey")
            data = self.objects[args["Key"]]
            return {
                "Body": io.BytesIO(data),
                "ContentLength": len(data),
                "ServerSideEncryption": "AES256",
            }

        def put_object(self, **args):
            self.writes.append(args)
            self.objects[args["Key"]] = args["Body"]
            return {}

        def head_bucket(self, **args):
            if self.denied:
                raise StubError()
            assert args["Bucket"] == settings.bucket
            assert args["ExpectedBucketOwner"] == settings.account
            return {}

        def get_bucket_location(self, **args):
            return {"LocationConstraint": self.region}

        def get_bucket_tagging(self, **args):
            return {"TagSet": [{"Key": k, "Value": v} for k, v in self.tags.items()]}

        def get_public_access_block(self, **args):
            return {
                "PublicAccessBlockConfiguration": self.security["public_access_block"]
            }

        def get_bucket_encryption(self, **args):
            return {"ServerSideEncryptionConfiguration": self.security["encryption"]}

        def get_bucket_ownership_controls(self, **args):
            return {"OwnershipControls": self.security["ownership"]}

        def get_bucket_versioning(self, **args):
            return self.security["versioning"]

        def get_bucket_lifecycle_configuration(self, **args):
            return self.security["lifecycle"]

        def get_bucket_policy(self, **args):
            return {"Policy": self.policy}

        def get_bucket_policy_status(self, **args):
            return {"PolicyStatus": {"IsPublic": self.public}}

        def list_object_versions(self, **args):
            return {"Versions": self.versions.copy(), "IsTruncated": False}

        def list_multipart_uploads(self, **args):
            return {"Uploads": self.uploads.copy(), "IsTruncated": False}

        def abort_multipart_upload(self, **args):
            self.aborts.append(args)
            self.uploads = [
                u for u in self.uploads if u["UploadId"] != args["UploadId"]
            ]

        def delete_objects(self, **args):
            self.deletes += args["Delete"]["Objects"]
            self.versions = [
                v
                for v in self.versions
                if {"Key": v["Key"], "VersionId": v["VersionId"]} not in self.deletes
            ]
            return {}

    return S3()


@pytest.fixture
def foundations(s3, settings):
    from types import SimpleNamespace

    from cloud.aws.policies import execution_boundary, execution_policy, trust_policy

    iam = SimpleNamespace(
        role={
            "Arn": settings.glue_role_arn,
            "Path": "/",
            "PermissionsBoundary": {
                "PermissionsBoundaryArn": settings.glue_boundary_arn
            },
            "AssumeRolePolicyDocument": trust_policy(settings),
            "Tags": [{"Key": k, "Value": v} for k, v in settings.tags.items()],
        },
        inline=execution_policy(settings),
        boundary=execution_boundary(settings),
        names=["bounded-etl"],
        attached=[],
    )
    iam.get_role = lambda **kw: {"Role": iam.role}
    iam.list_role_policies = lambda **kw: {"PolicyNames": iam.names}
    iam.list_attached_role_policies = lambda **kw: {"AttachedPolicies": iam.attached}
    iam.get_role_policy = lambda **kw: {"PolicyDocument": iam.inline}
    iam.get_policy = lambda **kw: {
        "Policy": {"Arn": settings.glue_boundary_arn, "DefaultVersionId": "v1"}
    }
    iam.get_policy_version = lambda **kw: {
        "PolicyVersion": {"Document": iam.boundary, "IsDefaultVersion": True}
    }
    return {"s3": s3, "iam": iam}
