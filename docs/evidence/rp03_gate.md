# RP-03 real-data gate — 2026-10-07

Status: **REAL-DATA VALIDATED — PASS**.

Executed `python -m retailpulse bronze` twice on unchanged real inputs.
First run: 56.685 seconds. Rerun: 4.529 seconds, `reused=True`.
Both returned run ID `47b8b962c868f3c60fc8` and ingestion timestamp
`2026-10-07T21:29:04.505820+00:00`. Output root:
`data/processed/bronze/runs/47b8b962c868f3c60fc8/`.

| Dataset | Input rows | Parquet rows |
| --- | ---: | ---: |
| calendar | 1,969 | 1,969 |
| prices | 6,841,121 | 6,841,121 |
| sales | 30,490 | 30,490 |

Files are `calendar.parquet`, `prices.parquet`, `sales.parquet`; the snapshot's
`summary.json` stores their counts, source SHA-256 and output SHA-256 values.
Every output checksum was independently verified. A full metadata grouping
found exactly one correct `source_file`, `source_checksum`, `pipeline_run_id`
and `ingestion_ts` value per source table. All original source columns and
source row counts were preserved. The rerun retained identical checksums,
counts and timestamp; no appended data or second active generation appeared.

Peak sampled process-tree working set was 1,781.96 MiB initially and 91.22 MiB
on reuse. The source hashes are recorded in [RP-02 evidence](rp02_gate.md).
All Bronze files are under ignored `data/processed/`; none are committed.
No Bronze implementation defect or dependency change was required.
