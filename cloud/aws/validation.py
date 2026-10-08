"""Offline-only infrastructure validation; refuses non-mocked Terraform tests."""

import os
import re
import subprocess
import sys
from pathlib import Path

from cloud.aws.contracts import LabError


def terraform_path(root):
    path = (
        Path(root)
        / "artifacts/rp12/tools"
        / ("terraform.exe" if os.name == "nt" else "terraform")
    )
    if not path.is_file():
        raise LabError("install_pinned_terraform_first")
    return path


def check_mock_tests(directory):
    tests = list(Path(directory).glob("tests/*.tftest.hcl"))
    if not tests or list(Path(directory).glob("tests/*.tftest.json")):
        raise LabError("unexpected_terraform_test_format")
    for path in tests:
        text = re.sub(r"(?m)#.*$", "", path.read_text(encoding="utf-8"))
        if (
            len(re.findall(r'\bmock_provider\s+"aws"\s*\{', text)) != 1
            or re.search(r'(?m)^\s*provider\s+"', text)
            or re.search(r"\bproviders\s*=|\bmodule\s*\{|\boverride_module\s*\{", text)
            or any(
                command != "plan"
                for command in re.findall(r"\bcommand\s*=\s*(\w+)", text)
            )
            or len(re.findall(r'\brun\s+"', text))
            != len(re.findall(r"\bcommand\s*=\s*plan\b", text))
        ):
            raise LabError("non_mocked_terraform_test_rejected")
    return len(tests)


def offline_environment(root):
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("AWS_", "TF_VAR_", "TF_CLI_ARGS"))
    }
    empty = Path(root) / "artifacts/rp12/empty-aws-config"
    empty.parent.mkdir(parents=True, exist_ok=True)
    empty.write_text("", encoding="utf-8")
    env.update(
        {
            "AWS_CONFIG_FILE": str(empty),
            "AWS_SHARED_CREDENTIALS_FILE": str(empty),
            "AWS_EC2_METADATA_DISABLED": "true",
            "CHECKPOINT_DISABLE": "1",
            "TF_IN_AUTOMATION": "1",
        }
    )
    return env


def validate(root):
    root = Path(root)
    check_mock_tests(root / "infra/aws")
    env = offline_environment(root)
    binary = str(terraform_path(root))
    results = []
    for args in (
        ["fmt", "-check", "-recursive"],
        ["init", "-backend=false", "-input=false", "-lockfile=readonly", "-no-color"],
        ["validate", "-no-color"],
        ["test", "-no-color"],
    ):
        result = subprocess.run(
            [binary, "-chdir=infra/aws", *args], cwd=root, env=env, check=False
        )
        results.append(
            {"command": "terraform " + " ".join(args), "exit_code": result.returncode}
        )
        if result.returncode:
            raise LabError("offline_terraform_validation_failed")
    import tempfile

    with tempfile.TemporaryDirectory(
        prefix="pytest-", dir=root / "artifacts/rp12"
    ) as base:
        # No credential discovery/network is allowed by tests/aws/conftest.py.
        env["PYTEST_ADDOPTS"] = "--basetemp=" + (Path(base) / "run").as_posix()
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/aws", "-p", "no:cacheprovider"],
            cwd=root,
            env=env,
            check=False,
        )
        if result.returncode:
            raise LabError("offline_cloud_tests_failed")
    return {
        "mode": "offline",
        "mock_provider_only": True,
        "terraform": results,
        "cloud_tests_exit": 0,
        "live_aws_calls": 0,
    }
