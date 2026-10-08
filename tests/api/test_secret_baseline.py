"""Real scanner regressions for exact exceptions and locale-independent UTF-8."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = "docs/evidence/real_m5_validation.json"


@pytest.fixture
def scan_repository(tmp_path):
    script = tmp_path / "scripts/scan_secrets.py"
    script.parent.mkdir()
    script.write_bytes((ROOT / "scripts/scan_secrets.py").read_bytes())
    evidence = tmp_path / EVIDENCE
    evidence.parent.mkdir(parents=True)
    evidence.write_bytes((ROOT / EVIDENCE).read_bytes())
    baseline = json.loads((ROOT / ".secrets.baseline").read_text(encoding="utf-8"))
    rows = baseline["results"][EVIDENCE]
    assert len(rows) == 6
    assert [r["line_number"] for r in rows] == [15, 29, 38, 75, 150, 193]
    baseline["results"] = {EVIDENCE: rows}
    (tmp_path / ".secrets.baseline").write_text(
        json.dumps(baseline), encoding="utf-8"
    )
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True)

    def scan():
        # Force the entry point to start without UTF-8 mode, even on Linux CI.
        result = subprocess.run(
            [sys.executable, "-X", "utf8=0", str(script)],
            cwd=tmp_path,
            env={**os.environ, "PYTHONUTF8": "0"},
            capture_output=True,
            check=False,
        )
        report = json.loads((tmp_path / "reports/secrets.json").read_text(encoding="utf-8"))
        assert result.returncode == (1 if report["result"] == "FAIL" else 0)
        return report, result.stdout + result.stderr

    return tmp_path, scan


def test_six_exact_provenance_exceptions_scan_utf8(scan_repository):
    root, scan = scan_repository
    # This is the encoding failure that previously hid the six findings on Windows.
    with pytest.raises(UnicodeDecodeError):
        (root / EVIDENCE).read_bytes().decode("cp1252")
    report, _ = scan()
    assert report["result"] == "PASS"
    assert report["reviewed_false_positives"] == 6
    assert report["unreviewed_findings"] == []


@pytest.mark.parametrize("change", ["new-token", "new-checksum", "different-file", "unreviewed"])
def test_exceptions_do_not_approve_new_findings(scan_repository, change):
    root, scan = scan_repository
    document = root / EVIDENCE
    payload = json.loads(document.read_text(encoding="utf-8"))
    sensitive = None
    if change == "new-token":
        # Disposable invalid token, never a credential; don't print it on failure.
        sensitive = "ghp_" + uuid4().hex + "Ab7q"
        payload["integration_token"] = sensitive
    elif change == "new-checksum":
        payload["sources"][0]["sha256"] = hashlib.sha256(uuid4().bytes).hexdigest()
    elif change == "different-file":
        (root / "other.json").write_text(
            json.dumps({"sha256": payload["sources"][0]["sha256"]}), encoding="utf-8"
        )
    else:
        path = root / ".secrets.baseline"
        baseline = json.loads(path.read_text(encoding="utf-8"))
        baseline["results"][EVIDENCE][0].pop("reason")
        path.write_text(json.dumps(baseline), encoding="utf-8")
    document.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    report, output = scan()
    assert report["result"] == "FAIL"
    assert report["unreviewed_findings"]
    expected_path = "other.json" if change == "different-file" else EVIDENCE
    assert any(row["file"] == expected_path for row in report["unreviewed_findings"])
    if sensitive:
        assert sensitive.encode() not in output
        assert sensitive not in json.dumps(report)
