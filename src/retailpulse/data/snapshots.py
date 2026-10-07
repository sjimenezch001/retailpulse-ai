"""Publish complete derived Parquet snapshots with checksum verification."""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from retailpulse.data.source import checksum, utc_now, write_json
from retailpulse.quality.checks import require


def snapshot_id(identity: dict) -> str:
    return hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:20]


def read_snapshot(directory: Path) -> tuple[dict[str, pd.DataFrame], dict]:
    pointer = json.loads((directory / "current.json").read_text(encoding="utf-8"))
    run_id = pointer["pipeline_run_id"]
    require(len(run_id) == 20 and all(c in "0123456789abcdef" for c in run_id),
            "Invalid derived snapshot ID")
    path = directory / "runs" / run_id
    summary = json.loads((path / "summary.json").read_text(encoding="utf-8"))
    require(summary["pipeline_run_id"] == run_id, "Derived snapshot identity mismatch")
    tables = {}
    for name, entry in summary["tables"].items():
        require(name.isidentifier(), "Invalid table name")
        file = path / f"{name}.parquet"
        require(file.is_file() and checksum(file) == entry["sha256"],
                f"Derived snapshot checksum mismatch: {name}")
        tables[name] = pd.read_parquet(file)
        require(len(tables[name]) == entry["rows"], f"Derived row count mismatch: {name}")
    return tables, summary


def publish_tables(directory: Path, tables: dict[str, pd.DataFrame], identity: dict,
                   metrics: dict) -> dict:
    run_id = snapshot_id(identity)
    runs = directory / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    destination = runs / run_id
    if not destination.exists():
        summary = {"pipeline_run_id": run_id, "created_at": utc_now(),
                   "identity": identity, "metrics": metrics, "tables": {}}
        with TemporaryDirectory(prefix="staging-", dir=runs) as temporary:
            staging = Path(temporary)
            for name, frame in tables.items():
                require(name.isidentifier(), "Invalid table name")
                file = staging / f"{name}.parquet"
                frame.to_parquet(file, index=False)
                summary["tables"][name] = {"rows": len(frame), "sha256": checksum(file)}
            write_json(staging / "summary.json", summary)
            staging.rename(destination)
    # Validate before advancing the current pointer, including on a rerun.
    summary = json.loads((destination / "summary.json").read_text(encoding="utf-8"))
    require(summary["identity"] == identity, "Snapshot identity conflict")
    for name, entry in summary["tables"].items():
        require(checksum(destination / f"{name}.parquet") == entry["sha256"],
                f"Derived snapshot checksum mismatch: {name}")
    pointer = directory / "current.json.tmp"
    write_json(pointer, {"pipeline_run_id": run_id})
    pointer.replace(directory / "current.json")
    return summary
