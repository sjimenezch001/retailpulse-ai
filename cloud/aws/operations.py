"""Future live operations. The CLI gates every entry before session creation."""

import json
import os
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from cloud.aws.athena import Queries, reconcile_and_publish
from cloud.aws.auth import check_expiry, client
from cloud.aws.contracts import LabError, canonical, digest, packaged_inputs
from cloud.aws.endpoint_check import smoke_test
from cloud.aws.ownership import (
    empty_owned_bucket,
    stop_workloads,
    validate_outputs,
    verify_resources,
    verify_state,
)
from cloud.aws.validation import terraform_path

SERVICES = ("s3", "glue", "athena", "iam", "logs", "lambda", "apigatewayv2")
RESOURCE_TYPES = {
    "aws_s3_bucket",
    "aws_s3_bucket_public_access_block",
    "aws_s3_bucket_ownership_controls",
    "aws_s3_bucket_server_side_encryption_configuration",
    "aws_s3_bucket_versioning",
    "aws_s3_bucket_policy",
    "aws_s3_bucket_lifecycle_configuration",
    "aws_cloudwatch_log_group",
    "aws_iam_role",
    "aws_iam_role_policy",
    "aws_glue_security_configuration",
    "aws_glue_job",
    "aws_glue_catalog_database",
    "aws_glue_catalog_table",
    "aws_athena_workgroup",
    "aws_lambda_function",
    "aws_apigatewayv2_api",
    "aws_apigatewayv2_integration",
    "aws_apigatewayv2_route",
    "aws_apigatewayv2_stage",
    "aws_lambda_permission",
}


class Operations:
    def __init__(self, root, settings, args, prepared, session):
        self.root, self.settings, self.args = Path(root), settings, args
        self.prepared, self.session = prepared, session
        self.directory = self.root / "artifacts/rp12/live" / settings.lab_id
        self.directory.mkdir(parents=True, exist_ok=True)
        self.state = self.directory / "terraform.tfstate"
        self.variables = self.directory / "lab.tfvars.json"
        self.planfile = self.directory / "reviewed.tfplan"
        self.clients = {name: client(session, name) for name in SERVICES}

    def tf(self, *arguments, capture=False):
        env = {
            k: v
            for k, v in os.environ.items()
            if not k.startswith(("AWS_", "TF_VAR_", "TF_CLI_ARGS"))
        }
        env.update(
            {
                "AWS_PROFILE": self.args.profile,
                "AWS_REGION": self.settings.region,
                "AWS_EC2_METADATA_DISABLED": "true",
                "TF_IN_AUTOMATION": "1",
                "CHECKPOINT_DISABLE": "1",
            }
        )
        for key in ("AWS_CONFIG_FILE", "AWS_SHARED_CREDENTIALS_FILE"):
            if key in os.environ:
                env[key] = os.environ[key]
        result = subprocess.run(
            [str(terraform_path(self.root)), "-chdir=infra/aws", *arguments],
            cwd=self.root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        # Terraform diagnostics/state stay local; never echo unknown provider messages.
        (self.directory / "last-terraform.log").write_text(
            result.stdout + result.stderr,
            encoding="utf-8",
        )
        if result.returncode:
            raise LabError("terraform_failed_inspect_local_log")
        return result.stdout if capture else None

    def initialize(self):
        self.tf(
            "init",
            "-input=false",
            "-reconfigure",
            "-lockfile=readonly",
            "-backend-config=path=" + self.state.as_posix(),
            "-no-color",
        )

    def outputs(self):
        if not self.state.is_file():
            raise LabError("expected_local_state_missing")
        outputs = json.loads(self.tf("output", "-json", "lab", capture=True))
        validate_outputs(outputs, self.settings)
        state = json.loads(
            self.tf("show", "-json", self.state.as_posix(), capture=True)
        )
        verify_state(state, self.settings, outputs)
        return outputs

    def infra_digest(self):
        files = [
            *sorted((self.root / "infra/aws").glob("*.tf")),
            *sorted((self.root / "infra/aws").glob("*.tf.json")),
            self.root / "infra/aws/.terraform.lock.hcl",
        ]
        return digest(canonical({p.name: digest(p.read_bytes()) for p in files}))

    def plan(self):
        if not self.args.service_access_reviewed:
            raise LabError("service_access_review_required")
        check_expiry(self.args.expires_on)
        variables = {
            "account_id": self.settings.account,
            "aws_region": self.settings.region,
            "aws_profile": self.args.profile,
            "environment": self.settings.environment,
            "expires_on": self.args.expires_on,
            "run_id": self.settings.run_id,
            "code_digest": self.prepared["code_digest"],
            "enable_endpoint": self.args.enable_endpoint,
            "lambda_bundle": (
                self.root / "artifacts/rp12/prepared/lambda.zip"
            ).as_posix(),
        }
        self.variables.write_bytes(canonical(variables) + b"\n")
        self.initialize()
        if self.state.is_file():
            self.outputs()  # Reject foreign identifiers before even planning changes.
        self.tf(
            "plan",
            "-input=false",
            "-var-file=" + self.variables.as_posix(),
            "-out=" + self.planfile.as_posix(),
            "-no-color",
        )
        plan = json.loads(
            self.tf("show", "-json", self.planfile.as_posix(), capture=True)
        )
        for resource in plan.get("resource_changes", []):
            if (
                resource["type"] not in RESOURCE_TYPES
                or resource.get("mode") != "managed"
            ):
                raise LabError("unexpected_plan_resource")
            before = resource["change"].get("before") or {}
            tags = before.get("tags_all") or before.get("tags")
            if tags and tags.get("LabId") != self.settings.lab_id:
                raise LabError("plan_contains_other_lab")
        receipt = {
            "account": self.settings.account,
            "region": self.settings.region,
            "environment": self.settings.environment,
            "run_id": self.settings.run_id,
            "plan_sha256": digest(self.planfile.read_bytes()),
            "variables_sha256": digest(self.variables.read_bytes()),
            "infra_sha256": self.infra_digest(),
            "resource_changes": len(plan.get("resource_changes", [])),
        }
        (self.directory / "plan_receipt.json").write_bytes(canonical(receipt) + b"\n")
        return {
            "saved_plan": str(self.planfile.relative_to(self.root)),
            "resource_changes": receipt["resource_changes"],
            "live_account_plan": True,
        }

    def deploy(self):
        if not self.args.service_access_reviewed:
            raise LabError("service_access_review_required")
        receipt = json.loads((self.directory / "plan_receipt.json").read_bytes())
        expected = {
            "account": self.settings.account,
            "region": self.settings.region,
            "environment": self.settings.environment,
            "run_id": self.settings.run_id,
            "plan_sha256": digest(self.planfile.read_bytes()),
            "variables_sha256": digest(self.variables.read_bytes()),
            "infra_sha256": self.infra_digest(),
        }
        if any(receipt.get(k) != v for k, v in expected.items()):
            raise LabError("reviewed_plan_changed")
        check_expiry(json.loads(self.variables.read_bytes())["expires_on"])
        self.initialize()
        self.tf("apply", "-input=false", "-no-color", self.planfile.as_posix())
        outputs = self.outputs()
        verify_resources(self.clients, self.settings, outputs)
        s3 = self.clients["s3"]
        base = self.root / "artifacts/rp12/prepared"
        for name in self.prepared["files"]:
            if name == "lambda.zip":
                continue  # Terraform supplies the reviewed local bundle directly.
            category = "input" if name.startswith("input/") else "scripts"
            filename = name.removeprefix("input/")
            s3.put_object(
                Bucket=self.settings.bucket,
                Key=self.settings.key(category, filename),
                Body=(base / name).read_bytes(),
                ServerSideEncryption="AES256",
                ExpectedBucketOwner=self.settings.account,
            )
        (self.directory / "inventory.json").write_bytes(canonical(outputs) + b"\n")
        return {
            "deployed": True,
            "input_upload_files": len(self.prepared["files"]) - 1,
            "lab_id": self.settings.lab_id,
        }

    def run_etl(self):
        outputs = self.outputs()
        verify_resources(self.clients, self.settings, outputs)
        glue = self.clients["glue"]
        job = glue.get_job(JobName=self.settings.name)["Job"]
        fixed = job.get("NonOverridableArguments", {})
        if (
            job.get("MaxRetries") != 0
            or job.get("Timeout") != 5
            or job.get("WorkerType") != "G.1X"
            or job.get("NumberOfWorkers") != 2
            or job.get("ExecutionProperty", {}).get("MaxConcurrentRuns") != 1
            or fixed.get("--LAB_RUN_ID") != self.settings.run_id
            or fixed.get("--CODE_DIGEST") != self.prepared["code_digest"]
        ):
            raise LabError("glue_limits_or_identity_changed")
        run_id = glue.start_job_run(
            JobName=self.settings.name,
            WorkerType="G.1X",
            NumberOfWorkers=2,
            Timeout=5,
        )["JobRunId"]
        terminal = False
        try:
            for _ in range(42):
                result = glue.get_job_run(JobName=self.settings.name, RunId=run_id)[
                    "JobRun"
                ]
                state = result["JobRunState"]
                if state in {
                    "SUCCEEDED",
                    "FAILED",
                    "TIMEOUT",
                    "ERROR",
                    "STOPPED",
                    "EXPIRED",
                }:
                    terminal = True
                    if state != "SUCCEEDED":
                        raise LabError("glue_job_failed")
                    return {
                        "job_run_id": run_id,
                        "state": state,
                        "live": True,
                        "execution_seconds": result.get("ExecutionTime"),
                    }
                time.sleep(10)
            raise LabError("glue_poll_timeout")
        finally:
            if not terminal:
                response = glue.batch_stop_job_run(
                    JobName=self.settings.name, JobRunIds=[run_id]
                )
                if response.get("Errors"):
                    raise LabError("glue_cancellation_unverified")

    def inventory(self):
        return verify_resources(self.clients, self.settings, self.outputs())

    def query_checks(self):
        self.inventory()
        _, trusted, _ = packaged_inputs(self.root)
        return reconcile_and_publish(
            Queries(self.clients["athena"], self.settings),
            self.clients["s3"],
            self.settings,
            trusted,
            self.prepared,
        )

    def endpoint_check(self):
        outputs = self.outputs()
        verify_resources(self.clients, self.settings, outputs)
        return smoke_test(
            self.session, self.settings, outputs, self.prepared["metric_reference"]
        )

    def teardown(self):
        outputs = self.outputs()
        verify_resources(self.clients, self.settings, outputs)
        # Preserve recovery information even after a successful destroy.
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        recovery = self.directory / f"recovery-{stamp}"
        recovery.mkdir()
        shutil.copyfile(self.state, recovery / "terraform.tfstate")
        (recovery / "inventory.json").write_bytes(canonical(outputs))
        stopped = stop_workloads(self.clients, self.settings, sleep=time.sleep)
        cleared = empty_owned_bucket(self.clients["s3"], self.settings)
        self.tf(
            "destroy",
            "-input=false",
            "-auto-approve",
            "-var-file=" + self.variables.as_posix(),
            "-no-color",
        )
        if self.tf("state", "list", capture=True).strip():
            raise LabError("terraform_resources_remain")
        # Exact resource absence checks; AccessDenied never counts as absence.
        checks = [
            (
                "s3_bucket",
                lambda: self.clients["s3"].head_bucket(
                    Bucket=self.settings.bucket,
                    ExpectedBucketOwner=self.settings.account,
                ),
                {"404", "NoSuchBucket"},
            ),
            (
                "glue_job",
                lambda: self.clients["glue"].get_job(JobName=self.settings.name),
                {"EntityNotFoundException"},
            ),
            (
                "catalog_database",
                lambda: self.clients["glue"].get_database(
                    CatalogId=self.settings.account, Name=self.settings.database
                ),
                {"EntityNotFoundException"},
            ),
            (
                "glue_security",
                lambda: self.clients["glue"].get_security_configuration(
                    Name=self.settings.name
                ),
                {"EntityNotFoundException"},
            ),
            (
                "workgroup",
                lambda: self.clients["athena"].get_work_group(
                    WorkGroup=self.settings.name
                ),
                {"InvalidRequestException"},
            ),
        ]
        for role in [outputs["glue_role"], outputs["lambda_role"]]:
            if role:
                checks.append(
                    (
                        "role:" + role,
                        lambda role=role: self.clients["iam"].get_role(RoleName=role),
                        {"NoSuchEntity"},
                    )
                )
        if outputs["api_id"]:
            checks += [
                (
                    "api",
                    lambda: self.clients["apigatewayv2"].get_api(
                        ApiId=outputs["api_id"]
                    ),
                    {"NotFoundException"},
                ),
                (
                    "lambda",
                    lambda: self.clients["lambda"].get_function(
                        FunctionName=outputs["function"]
                    ),
                    {"ResourceNotFoundException"},
                ),
            ]
        unverified = []
        for label, call, codes in checks:
            try:
                call()
            except Exception as exc:
                error = getattr(exc, "response", {}).get("Error", {})
                if error.get("Code") not in codes:
                    unverified.append(label)
                elif label == "workgroup" and not any(
                    phrase in error.get("Message", "").lower()
                    for phrase in ("not found", "does not exist")
                ):
                    unverified.append(label)
            else:
                unverified.append(label)
        for group in outputs["log_groups"]:
            try:
                result = self.clients["logs"].describe_log_groups(
                    logGroupNamePrefix=group,
                    limit=50,
                )
                if result.get("nextToken") or any(
                    g["logGroupName"] == group for g in result["logGroups"]
                ):
                    unverified.append("log:" + group)
            except Exception:
                unverified.append("log:" + group)
        report = {
            "stopped": stopped,
            "s3_cleanup": cleared,
            "unverified_or_remaining": unverified,
            "recovery_preserved": True,
            "complete": not unverified,
            "live": True,
        }
        (self.directory / "teardown.json").write_bytes(canonical(report) + b"\n")
        if unverified:
            raise LabError("teardown_incomplete_inspect_local_report")
        return report
