"""Scan every tracked working-tree file with pinned detect-secrets; fail closed."""

import hashlib
import json
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path

from detect_secrets import SecretsCollection
from detect_secrets.settings import default_settings

ROOT = Path(__file__).resolve().parents[1]


def main():
    files = (
        subprocess.check_output(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            cwd=ROOT,
        )
        .decode()
        .split("\0")
    )
    files = sorted(set(p for p in files if p and (ROOT / p).is_file()))
    for filename in files:
        if not (ROOT / filename).resolve().is_relative_to(ROOT):
            raise ValueError("A tracked file resolves outside the repository")
        with (ROOT / filename).open("rb") as stream:
            stream.read(1)
    baseline = json.loads((ROOT / ".secrets.baseline").read_text(encoding="utf-8"))
    approved = {
        (path, row["type"], row["hashed_secret"])
        for path, rows in baseline["results"].items()
        for row in rows
        if row.get("is_secret") is False and row.get("reason")
    }
    collection = SecretsCollection()
    fingerprint_metadata = {
        (
            ".secrets.baseline",
            detector,
            hashlib.sha1(row["hashed_secret"].encode()).hexdigest(),
        )
        for rows in baseline["results"].values()
        for row in rows
        for detector in ("Hex High Entropy String", "Secret Keyword")
    }
    with default_settings():
        # Scan the baseline too. Only exact fingerprint values are metadata.
        collection.scan_files(*files, num_processors=1)
    findings = collection.json()
    unexpected = []
    reviewed = 0
    metadata = 0
    for path, rows in findings.items():
        for row in rows:
            key = (path.replace("\\", "/"), row["type"], row["hashed_secret"])
            if key in approved:
                reviewed += 1
            elif key in fingerprint_metadata:
                metadata += 1
            else:
                unexpected.append(
                    {"file": key[0], "line": row["line_number"], "type": row["type"]}
                )
    report = {
        "scanner": "detect-secrets",
        "version": version("detect-secrets"),
        "scope": "All tracked files plus non-ignored untracked files; current tree, not Git history",
        "files_scanned": len(files),
        "reviewed_false_positives": reviewed,
        "baseline_fingerprint_metadata": metadata,
        "unreviewed_findings": unexpected,
        "result": "FAIL" if unexpected else "PASS",
    }
    destination = ROOT / "reports/secrets.json"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))
    return bool(unexpected)


if __name__ == "__main__":
    # detect-secrets opens text with the process default encoding and silently
    # skips decoding failures as binary files. Use UTF-8 on Windows as on Linux.
    if not sys.flags.utf8_mode:
        sys.exit(
            subprocess.call(
                [sys.executable, "-X", "utf8", str(Path(__file__).resolve()), *sys.argv[1:]]
            )
        )
    sys.exit(main())
