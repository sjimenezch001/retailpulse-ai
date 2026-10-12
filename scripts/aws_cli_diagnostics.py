"""Safe local AWS CLI receipts; no authentication or AWS calls on import."""

import hashlib
import re


def raw_bytes(value):
    if value is None:
        return b""
    return (
        value if isinstance(value, bytes) else value.encode("utf-8", errors="replace")
    )


def sanitize(value):
    text = raw_bytes(value).decode("utf-8", errors="replace")
    text = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", text)
    text = re.sub(
        r"(?im)^.*(?:access[_ -]?key|secret[_ -]?key|credential|authorization|token|password).*$",
        "[credential-bearing diagnostic redacted]",
        text,
    )
    text = re.sub(r"(?i)(?:https?://)[^\s]+", "[URL redacted]", text)
    text = re.sub(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b", "[access-key redacted]", text)
    text = re.sub(r"(?i)(bearer\s+)[^\s]+", r"\1[redacted]", text)
    text = re.sub(r"[A-Za-z0-9_+/=-]{32,}", "[long identifier redacted]", text)
    text = re.sub(r"(?i)(mfa[^\n]{0,40}code[^\n]{0,10})\d{6}", r"\1[redacted]", text)
    return re.sub(r"\b\d{6}\b", "[six-digit value redacted]", text)[:6000]


def record_cli_outcome(entry, *, exit_code, stderr, status):
    """Record process outcome before sanitizing; fail closed on sanitizer errors.

    A timeout has no observed exit code and must use None, never a fabricated
    success code. Callers must persist this receipt and stop if False is returned.
    Raw stderr and exception messages must never be used as a fallback.
    """
    entry.update(
        exit_code=exit_code,
        status=status,
        stderr_sha256=hashlib.sha256(raw_bytes(stderr)).hexdigest(),
    )
    try:
        entry["sanitized_stderr"] = sanitize(stderr)
    except Exception as error:
        entry["sanitized_stderr"] = "[sanitization failed; raw stderr withheld]"
        entry["diagnostic_error"] = type(error).__name__
        return False
    return True
