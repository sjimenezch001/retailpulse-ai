import hashlib

import pytest
from scripts import aws_cli_diagnostics as diagnostics


@pytest.mark.parametrize("exit_code", [0, 1, 254, 255])
def test_cli_exit_and_safe_stderr_are_recorded(exit_code):
    stderr = "An error occurred (AccessDenied) calling ListRolePolicies\n"
    entry = {"operation": "list-role-policies"}
    assert diagnostics.record_cli_outcome(
        entry, exit_code=exit_code, stderr=stderr, status="COMPLETED"
    )
    assert entry["exit_code"] == exit_code
    assert entry["sanitized_stderr"] == stderr
    assert entry["stderr_sha256"] == hashlib.sha256(stderr.encode()).hexdigest()


@pytest.mark.parametrize("stderr", [None, b"read timed out", "read timed out"])
def test_timeout_never_invents_exit_code(stderr):
    entry = {}
    assert diagnostics.record_cli_outcome(
        entry, exit_code=None, stderr=stderr, status="TIMEOUT"
    )
    assert entry["exit_code"] is None and entry["status"] == "TIMEOUT"


def test_credentials_urls_and_mfa_are_redacted():
    # Synthetic format-valid test input, not an issued credential. Build it at
    # runtime so the unchanged repository scanner can detect real literal keys.
    fake_access_key = "".join(("ASIA", "ABCDEFGHIJKLMNOP"))
    stderr = (
        "AccessDenied\nsecret_key=private-value\nMFA code 123456\n"
        f"https://example.test/?private=value\n{fake_access_key}\n"
    )
    output = diagnostics.sanitize(stderr.encode())
    assert "AccessDenied" in output
    for private in ("private-value", "123456", "example.test", fake_access_key):
        assert private not in output


@pytest.mark.parametrize("exit_code,status", [(255, "FAILED"), (None, "TIMEOUT")])
def test_diagnostic_failure_preserves_process_outcome_without_raw_stderr(
    monkeypatch, exit_code, status
):
    def broken_sanitizer(value):
        raise NameError("secret=must-not-be-exposed")

    monkeypatch.setattr(diagnostics, "sanitize", broken_sanitizer)
    entry = {"operation": "get-caller-identity"}
    assert not diagnostics.record_cli_outcome(
        entry, exit_code=exit_code, stderr="token=private", status=status
    )
    assert entry["exit_code"] == exit_code and entry["status"] == status
    assert entry["operation"] == "get-caller-identity"
    assert entry["diagnostic_error"] == "NameError"
    assert "private" not in repr(entry) and "must-not-be-exposed" not in repr(entry)
