from types import SimpleNamespace

import pytest
from cloud.aws import auth
from cloud.aws.auth import (
    authenticated_session,
    check_expiry,
    require_selection,
    validate_identity,
)
from cloud.aws.contracts import LabError
from cloud.aws.ownership import empty_owned_bucket, validate_outputs, verify_bucket
from cloud.aws.validation import check_mock_tests, offline_environment


def test_live_operations_require_explicit_authorization():
    args = SimpleNamespace(
        operation="deploy",
        profile="selected",
        account="111111111111",
        region="sa-east-1",
        environment="lab",
        authorize_live=False,
        budget_reviewed=True,
        confirm=None,
    )
    with pytest.raises(LabError, match="separate_authorization"):
        require_selection(args)
    args.authorize_live = True
    with pytest.raises(LabError, match="confirmation"):
        require_selection(args)
    args.confirm = "deploy:111111111111:sa-east-1:lab"
    require_selection(args)
    args.budget_reviewed = False
    with pytest.raises(LabError, match="budget"):
        require_selection(args)


@pytest.mark.parametrize(
    "arn",
    [
        "arn:aws:iam::000000000000:root",
        "arn:aws:iam::000000000000:user/example",
        "arn:aws:sts::999999999999:assumed-role/example/session",
    ],
)
def test_root_user_and_wrong_account_identity_rejected(arn):
    with pytest.raises(LabError):
        validate_identity({"Account": "000000000000", "Arn": arn}, "000000000000")


def test_wrong_account_rejected_even_with_role():
    with pytest.raises(LabError, match="wrong_account"):
        validate_identity(
            {
                "Account": "999999999999",
                "Arn": "arn:aws:sts::999999999999:assumed-role/example/session",
            },
            "000000000000",
        )


def session_factory(region="sa-east-1", token="offline", fail=False):
    def factory(**kwargs):
        if fail:
            raise RuntimeError("stub credential exception")
        scoped = SimpleNamespace(get_scoped_config=lambda: {"region": region})
        credentials = SimpleNamespace(
            get_frozen_credentials=lambda: SimpleNamespace(token=token)
        )
        return SimpleNamespace(_session=scoped, get_credentials=lambda: credentials)

    return factory


def test_profile_and_temporary_credential_requirements(monkeypatch, settings):
    monkeypatch.setattr(
        auth,
        "client",
        lambda *args: SimpleNamespace(
            get_caller_identity=lambda: {
                "Account": settings.account,
                "Arn": f"arn:aws:sts::{settings.account}:assumed-role/example/session",
            }
        ),
    )
    assert authenticated_session("selected", settings, session_factory())
    with pytest.raises(LabError, match="region"):
        authenticated_session("selected", settings, session_factory(region="us-east-1"))
    with pytest.raises(LabError, match="temporary_credentials"):
        authenticated_session("selected", settings, session_factory(token=None))
    with pytest.raises(LabError, match="missing_expired_or_denied"):
        authenticated_session("selected", settings, session_factory(fail=True))
    with pytest.raises(LabError, match="explicit_profile"):
        authenticated_session("", settings, session_factory())
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "offline")
    with pytest.raises(LabError, match="ambient"):
        authenticated_session("selected", settings, session_factory())


def test_denied_identity_is_sanitized(monkeypatch, settings):
    def denied(*args):
        raise RuntimeError("stub private service response")

    monkeypatch.setattr(auth, "client", denied)
    with pytest.raises(LabError, match="missing_expired_or_denied") as error:
        authenticated_session("selected", settings, session_factory())
    assert "private" not in str(error.value)


@pytest.mark.parametrize(
    "change", ["account", "region", "bucket", "lab_id", "log_groups"]
)
def test_exact_terraform_inventory_required(outputs, settings, change):
    outputs[change] = [] if change == "log_groups" else "unapproved"
    with pytest.raises(LabError):
        validate_outputs(outputs, settings)


def test_bucket_owner_tags_region_not_name_prefix(s3, settings):
    assert verify_bucket(s3, settings) is None
    s3.tags["LabId"] = "different"
    with pytest.raises(LabError, match="ownership"):
        empty_owned_bucket(s3, settings)
    assert not s3.deletes
    s3.tags = settings.tags.copy()
    s3.region = "us-east-1"
    with pytest.raises(LabError, match="region"):
        empty_owned_bucket(s3, settings)


def test_cleanup_handles_versions_and_incomplete_uploads(s3, settings):
    key = settings.key("curated", "example.parquet")
    s3.versions = [
        {"Key": key, "VersionId": "stub-v1"},
        {"Key": key, "VersionId": "stub-v2"},
    ]
    s3.uploads = [{"Key": settings.key("temporary", "part"), "UploadId": "stub-upload"}]
    result = empty_owned_bucket(s3, settings)
    assert result == {"object_versions_removed": 2, "multipart_uploads_aborted": 1}
    assert not s3.versions and not s3.uploads


def test_unknown_object_prevents_any_deletion(s3, settings):
    s3.versions = [
        {"Key": settings.key("input", "manifest.json"), "VersionId": "stub"},
        {"Key": "private/unexpected", "VersionId": "stub"},
    ]
    with pytest.raises(LabError, match="unexpected_object"):
        empty_owned_bucket(s3, settings)
    assert not s3.deletes and not s3.aborts


def test_denied_bucket_is_not_treated_as_absent(s3, settings):
    s3.denied = True
    with pytest.raises(Exception):
        empty_owned_bucket(s3, settings)
    assert not s3.deletes


def test_offline_environment_drops_ambient_configuration(monkeypatch, tmp_path):
    monkeypatch.setenv("AWS_PROFILE", "unapproved")
    monkeypatch.setenv("TF_VAR_aws_profile", "unapproved")
    monkeypatch.setenv("TF_CLI_ARGS_test", "unapproved")
    env = offline_environment(tmp_path)
    assert "AWS_PROFILE" not in env and "TF_VAR_aws_profile" not in env
    assert "TF_CLI_ARGS_test" not in env and env["AWS_EC2_METADATA_DISABLED"] == "true"


@pytest.mark.parametrize(
    "bad",
    [
        'provider "aws" {}',
        'run "bad" { command = apply }',
        'run "bad" { command = plan module { source = "../real" } }',
        'run "bad" { command = plan providers = { aws = aws.live } }',
    ],
)
def test_nonmocked_tests_cannot_run(root, tmp_path, bad):
    assert check_mock_tests(root / "infra/aws") == 1
    directory = tmp_path / "tests"
    directory.mkdir()
    (directory / "bad.tftest.hcl").write_text('mock_provider "aws" {}\n' + bad)
    with pytest.raises(LabError, match="non_mocked"):
        check_mock_tests(tmp_path)


def test_expiry_is_not_indefinite():
    with pytest.raises(LabError):
        check_expiry("2099-01-01")
