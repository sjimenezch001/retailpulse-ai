"""Audit all pins explicitly and reject incomplete scanner coverage."""

import json
import subprocess
import sys
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[1]


def expected_pins():
    expected = {}
    for filename in ("requirements.txt", "requirements-dev.txt"):
        for line in (ROOT / filename).read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.startswith(("#", "-r ")):
                continue
            requirement = Requirement(line)
            pins = list(requirement.specifier)
            if len(pins) != 1 or pins[0].operator != "==":
                raise ValueError("Security auditing requires exact dependency pins")
            expected[canonicalize_name(requirement.name)] = pins[0].version
    return expected


def validate_scope(report):
    actual = {
        canonicalize_name(row["name"]): row.get("version")
        for row in report["dependencies"]
        if not row.get("skip_reason")
    }
    if actual != expected_pins():
        raise ValueError("Dependency audit did not cover every pinned package/version")


def main():
    (ROOT / "reports").mkdir(exist_ok=True)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip_audit",
            "-r",
            "requirements.txt",
            "-r",
            "requirements-dev.txt",
            "--no-deps",
            "--disable-pip",
            "--strict",
            "--progress-spinner",
            "off",
            "--format",
            "json",
            "--output",
            "reports/dependencies.json",
        ],
        cwd=ROOT,
    )
    report = json.loads(
        (ROOT / "reports/dependencies.json").read_text(encoding="utf-8")
    )
    validate_scope(report)
    print(
        f"Verified audit scope: {len(expected_pins())} pinned packages; no skipped entries."
    )
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
