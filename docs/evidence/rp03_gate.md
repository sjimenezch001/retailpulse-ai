# RP-03 gate — 2026-10-07

Status: CODE COMPLETE; REAL-DATA VALIDATION PENDING.

`python -m retailpulse bronze` reads the configured three source files and
preserves each source table in Parquet. A run ID derives from source SHA-256
checksums and the ingestion contract version. Unchanged reruns verify and reuse
the immutable snapshot, including its original ingestion timestamp. Changed
sources create a new snapshot; `current.json` selects one complete generation.
There is no append or row duplication. Writes assume one local pipeline writer.

Each row has `ingestion_ts`, `source_file`, `source_checksum`, `pipeline_run_id`.
The structured `summary.json` reconciles input/output counts and stores output
checksums. Missing, empty or malformed sources and corrupted output fail loudly.
Incomplete runs do not replace the active snapshot. Historical snapshots are
retained under the ignored output directory for traceability.

Validation: `python -m pytest -p no:cacheprovider` → `16 passed in 1.74s`;
`python -m ruff check .` → `All checks passed!`.
Tests use only synthetic fixtures and temporary directories. No real M5
execution or real ingestion counts are claimed. Real ingestion remains pending.
Dependencies are unchanged.
