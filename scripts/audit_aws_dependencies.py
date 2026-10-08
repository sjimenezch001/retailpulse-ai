"""Audit every isolated AWS dependency pin; unknown, skipped or missing entries fail."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    pins = {}
    for line in (ROOT / "cloud/aws/requirements.txt").read_text().splitlines():
        if line and not line.startswith("#"):
            name, version = line.split("==")
            pins[name.lower().replace("_", "-")] = version
    report = ROOT / "reports/aws_dependencies.json"
    report.parent.mkdir(exist_ok=True)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip_audit",
            "--strict",
            "--no-deps",
            "--disable-pip",
            "-r",
            str(ROOT / "cloud/aws/requirements.txt"),
            "-f",
            "json",
            "-o",
            str(report),
        ],
        cwd=ROOT,
        check=False,
    )
    if result.returncode:
        return result.returncode
    rows = json.loads(report.read_text(encoding="utf-8"))["dependencies"]
    actual = {r["name"].lower().replace("_", "-"): r.get("version") for r in rows}
    if actual != pins or any(r.get("skip_reason") or r.get("vulns") for r in rows):
        raise ValueError("The complete isolated dependency audit did not pass")
    print(f"PASS: {len(pins)} isolated pins, zero skips, zero known vulnerabilities")
    return 0


if __name__ == "__main__":
    sys.exit(main())
