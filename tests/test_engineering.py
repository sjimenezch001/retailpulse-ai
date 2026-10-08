"""Regression checks for complete auditing and portable dependency locks."""

import importlib.util
from pathlib import Path

import pytest
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ROOT = Path(__file__).resolve().parents[1]


def audit_module():
    spec = importlib.util.spec_from_file_location(
        "audit_dependencies", ROOT / "scripts/audit_dependencies.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "failure", ["missing_runtime", "skipped_lookup", "wrong_version"]
)
def test_incomplete_or_wrong_audit_cannot_pass(failure):
    audit = audit_module()
    rows = [
        {"name": name, "version": version}
        for name, version in audit.expected_pins().items()
    ]
    audit.validate_scope({"dependencies": rows})
    runtime = next(r for r in rows if r["name"] == "duckdb")
    if failure == "missing_runtime":
        rows.remove(runtime)
    elif failure == "skipped_lookup":
        runtime["skip_reason"] = "Advisory service unavailable"
    else:
        runtime["version"] = "0.0.0"
    with pytest.raises(ValueError, match="every pinned"):
        audit.validate_scope({"dependencies": rows})


def test_container_runtime_pins_match_validated_lock():
    pins = audit_module().expected_pins()
    for line in (ROOT / "requirements-runtime.txt").read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        requirement = Requirement(line)
        assert pins[canonicalize_name(requirement.name)] in requirement.specifier
    assert (
        "playwright" not in (ROOT / "requirements-runtime.txt").read_text().casefold()
    )
