"""Immutable, content-addressed Bronze snapshots with a current-run pointer."""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd
import pyarrow.parquet as pq

from retailpulse.data.source import FILES, checksum, read_sources, utc_now, write_json

BRONZE_VERSION = "bronze-v1"


def _publish_current(directory: Path, run_id: str) -> None:
    pointer = directory / "current.json.tmp"
    write_json(pointer, {"pipeline_run_id": run_id})
    pointer.replace(directory / "current.json")


def verify_snapshot(snapshot: Path) -> dict:
    summary = json.loads((snapshot / "summary.json").read_text(encoding="utf-8"))
    if summary["pipeline_run_id"] != snapshot.name:
        raise ValueError("Bronze snapshot identity mismatch")
    for name in FILES:
        entry = summary["tables"][name]
        path = snapshot / f"{name}.parquet"
        if not path.is_file() or checksum(path) != entry["output_checksum"]:
            raise ValueError(f"Bronze checksum mismatch: {name}")
        count = pq.ParquetFile(path).metadata.num_rows
        if count != entry["input_rows"] or count != entry["output_rows"]:
            raise ValueError(f"Bronze row count mismatch: {name}")
    return summary


def ingest(directory: Path, output: Path) -> dict:
    hashes = {}
    for name, filename in FILES.items():
        path = directory / filename
        if not path.is_file() or not path.stat().st_size:
            raise ValueError(f"Missing or empty required source: {filename}")
        hashes[name] = checksum(path)
    identity = json.dumps({"version": BRONZE_VERSION, "sources": hashes}, sort_keys=True)
    run_id = hashlib.sha256(identity.encode()).hexdigest()[:20]
    output.mkdir(parents=True, exist_ok=True)
    snapshots = output / "runs"
    snapshots.mkdir(exist_ok=True)
    snapshot = snapshots / run_id
    if snapshot.exists():
        summary = verify_snapshot(snapshot)
        _publish_current(output, run_id)
        return {**summary, "reused": True}
    frames = read_sources(directory)
    if hashes != {k: checksum(directory / f) for k, f in FILES.items()}:
        raise ValueError("Source files changed during ingestion; retry a stable input")
    timestamp = utc_now()
    summary = {"pipeline_run_id": run_id, "ingestion_ts": timestamp,
               "version": BRONZE_VERSION, "tables": {}}
    # Stage all tables before exposing a complete generation. Single local writer.
    with TemporaryDirectory(prefix="staging-", dir=snapshots) as temporary:
        staging = Path(temporary)
        for name, frame in frames.items():
            reserved = {"ingestion_ts", "source_file", "source_checksum", "pipeline_run_id"}
            if reserved & set(frame):
                raise ValueError(f"Source contains reserved metadata fields: {name}")
            enriched = frame.assign(ingestion_ts=timestamp, source_file=FILES[name],
                                    source_checksum=hashes[name], pipeline_run_id=run_id)
            path = staging / f"{name}.parquet"
            enriched.to_parquet(path, index=False, engine="pyarrow")
            rows = pq.ParquetFile(path).metadata.num_rows
            if rows != len(frame):
                raise ValueError(f"Ingestion row count mismatch: {name}")
            summary["tables"][name] = {
                "source_file": FILES[name], "source_checksum": hashes[name],
                "input_rows": len(frame), "output_rows": rows,
                "output_checksum": checksum(path),
            }
        write_json(staging / "summary.json", summary)
        staging.rename(snapshot)
    verify_snapshot(snapshot)
    _publish_current(output, run_id)
    return {**summary, "reused": False}


def read_bronze(directory: Path) -> tuple[dict[str, pd.DataFrame], dict]:
    current = json.loads((directory / "current.json").read_text(encoding="utf-8"))
    run_id = current["pipeline_run_id"]
    if len(run_id) != 20 or any(c not in "0123456789abcdef" for c in run_id):
        raise ValueError("Invalid Bronze run ID")
    snapshot = directory / "runs" / run_id
    summary = verify_snapshot(snapshot)
    return {name: pd.read_parquet(snapshot / f"{name}.parquet") for name in FILES}, summary
