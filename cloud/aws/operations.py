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
from cloud.aws.foundations import verify_foundations
from cloud.aws.ownership import (
    FOUNDATION_DATA_TYPES,
    MANAGED_TYPES,
    empty_owned_bucket,
    stop_workloads,
    validate_outputs,
    verify_resources,
    verify_state,
)
from cloud.aws.validation import terraform_path

SERVICES = ("s3", "glue", "athena", "iam", "logs")
RESOURCE_TYPES = MANAGED_TYPES


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

    def foundation_check(self):
        return verify_foundations(self.clients, self.settings)

    def plan(self):
        if not self.args.service_access_reviewed:
            raise LabError("service_access_review_required")
        check_expiry(self.args.expires_on)
        foundations = self.foundation_check()
        variables = {
            "account_id": self.settings.account,
            "aws_region": self.settings.region,
            "aws_profile": self.args.profile,
            "environment": self.settings.environment,
            "expires_on": self.args.expires_on,
            "run_id": self.settings.run_id,
            "code_digest": self.prepared["code_digest"],
            "enable_endpoint": False,
            "owner_bucket_name": self.settings.bucket,
            "owner_glue_role_arn": self.settings.glue_role_arn,
            "owner_glue_boundary_arn": self.settings.glue_boundary_arn,
            "bucket_policy_sha256": foundations["bucket_policy_sha256"],
            "boundary_policy_sha256": foundations["boundary_sha256"],
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
            if resource.get("mode") == "data":
                if resource["type"] not in FOUNDATION_DATA_TYPES or any(
                    a not in {"read", "no-op"} for a in resource["change"]["actions"]
                ):
                    raise LabError("unexpected_foundation_plan")
                continue
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
            "foundations": foundations,
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
        if receipt.get("foundations") != self.foundation_check():
            raise LabError("reviewed_foundations_changed")
        check_expiry(json.loads(self.variables.read_bytes())["expires_on"])
        self.initialize()
        self.tf("apply", "-input=false", "-no-color", self.planfile.as_posix())
        outputs = self.outputs()
        verify_resources(self.clients, self.settings, outputs)
        s3 = self.clients["s3"]
        base = self.root / "artifacts/rp12/prepared"
        for name in self.prepared["files"]:
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
            "input_upload_files": len(self.prepared["files"]),
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
        raise LabError("endpoint_deferred")

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
                "workgroup",
                lambda: self.clients["athena"].get_work_group(
                    WorkGroup=self.settings.name
                ),
                {"InvalidRequestException"},
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
        foundations = self.foundation_check()
        report = {
            "owner_foundations_preserved": foundations,
            "owner_cleanup": "PENDING; separate manual bucket/role/boundary cleanup",
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
