"""Explicit temporary, non-root credentials only for separately authorized live commands."""

import os
import re
from datetime import date

from cloud.aws.contracts import LabError, iso_date


def require_selection(args):
    if not all(
        getattr(args, key, None)
        for key in ("profile", "account", "region", "environment")
    ):
        raise LabError("explicit_account_profile_region_environment_required")
    if not re.fullmatch(r"\d{12}", args.account) or args.account == "000000000000":
        raise LabError("invalid_live_account")
    if not getattr(args, "authorize_live", False):
        raise LabError("live_operation_requires_separate_authorization")
    if args.operation in {
        "plan",
        "deploy",
        "run-etl",
        "query-checks",
        "endpoint-check",
        "teardown",
    }:
        expected = f"{args.operation}:{args.account}:{args.region}:{args.environment}"
        if args.confirm != expected:
            raise LabError("explicit_operation_confirmation_required")
    if args.operation in {
        "plan",
        "deploy",
        "run-etl",
        "query-checks",
        "endpoint-check",
    }:
        if not args.budget_reviewed:
            raise LabError("gross_consumption_budget_review_required")


def validate_identity(identity, account):
    arn = identity.get("Arn", "")
    if arn.endswith(":root"):
        raise LabError("root_identity_rejected")
    if identity.get("Account") != account:
        raise LabError("wrong_account")
    if not arn.startswith(f"arn:aws:sts::{account}:assumed-role/"):
        # Root and long-lived IAM users are both excluded from this lab runner.
        raise LabError("temporary_assumed_role_required")


def authenticated_session(profile, settings, factory=None):
    # Never fall back to environment credentials, instance metadata or another profile.
    if any(
        os.environ.get(k)
        for k in (
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "AWS_SESSION_TOKEN",
            "AWS_WEB_IDENTITY_TOKEN_FILE",
            "AWS_ROLE_ARN",
            "AWS_CONTAINER_CREDENTIALS_FULL_URI",
            "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI",
            "AWS_ENDPOINT_URL",
        )
    ):
        raise LabError("ambient_credentials_or_endpoint_override_rejected")
    if any(k.startswith("AWS_ENDPOINT_URL") for k in os.environ):
        raise LabError("ambient_endpoint_override_rejected")
    if not profile:
        raise LabError("explicit_profile_required")
    os.environ["AWS_EC2_METADATA_DISABLED"] = "true"
    try:
        if factory is None:
            import boto3

            factory = boto3.Session
        session = factory(profile_name=profile, region_name=settings.region)
        config = session._session.get_scoped_config()
        if config.get("region") != settings.region or (
            config.get("endpoint_url") or config.get("services")
        ):
            raise LabError("profile_region_or_endpoint_mismatch")
        if config.get("credential_source") in {"Ec2InstanceMetadata", "EcsContainer"}:
            raise LabError("metadata_credential_source_rejected")
        credentials = session.get_credentials()
        if credentials is None or not credentials.get_frozen_credentials().token:
            raise LabError("temporary_credentials_required")
        identity = client(session, "sts").get_caller_identity()
        validate_identity(identity, settings.account)
        return session
    except LabError:
        raise
    except Exception as exc:
        raise LabError("credentials_missing_expired_or_denied") from exc


def client(session, service):
    if service not in {
        "sts",
        "s3",
        "glue",
        "athena",
        "lambda",
        "apigatewayv2",
        "logs",
        "iam",
    }:
        raise LabError("service_not_allowlisted")
    from botocore.config import Config

    return session.client(
        service,
        config=Config(
            connect_timeout=3,
            read_timeout=10,
            retries={"total_max_attempts": 1},
        ),
    )


def check_expiry(value):
    days = (iso_date(value) - date.today()).days
    if not 0 <= days <= 7:
        raise LabError("expiry_must_be_within_seven_days")
