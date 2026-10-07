# RP-02 real-data gate — 2026-10-07

Status: **REAL-DATA VALIDATED — PASS**.

Executed `python -m retailpulse profile --select-pilot --sample` against the
three real M5 files in ignored `data/raw/m5/`. Runtime: 75.837 seconds.

| Source | Bytes | Rows | Columns |
| --- | ---: | ---: | ---: |
| calendar.csv | 103,469 | 1,969 | 14 |
| sell_prices.csv | 203,395,785 | 6,841,121 | 4 |
| sales_train_evaluation.csv | 121,736,518 | 30,490 | 1947 |

SHA-256 values were independently recomputed and matched the real manifest:

- `calendar.csv`: `d12b5914ef03e66649adf5dd9e996e6602251c22b7a6af8f1f7e3aa12f8860f5`
- `sell_prices.csv`: `9da3ad1f8b8ccacdbdc70612191dd375ec24a4ac6625c24b75b3bc60b0bed2ef`
- `sales_train_evaluation.csv`: `4b4a47c44c38380d2a9168216fea8c9ff2f31b1ddb772f8a0995952a038b8aa0`

No duplicate rows or required-field schema problems were reported. Sales and
prices have no null cells. Calendar nulls are expected absent events: 1,807 in
each first-event name/type column and 1,964 in each second-event column.
Calendar dates span 2011-01-29–2016-06-19 (1,969 dates, 282 retail weeks).
Observed sales cover `d_1`–`d_1941`, 2011-01-29–2016-05-22. Source cardinalities:
10 stores, 7 departments, 3 categories, 3 states, 3,049 items and 30,490 series.
All daily sales columns are non-null int64, with observed bounds 0–763 units.

Price coverage across observed series × retail weeks is 6,719,161 / 8,476,220
(79.270724%). Future calendar weeks are excluded. Full per-column null counts
and cardinalities are retained in `data/contracts/raw_manifest.json`.

The deterministic rule selected `CA_1`, `CA_2`, `CA_3` and `FOODS_1`, `FOODS_2`.
Configuration was updated only from the actual source. The genuine sample is
six rows (36,243 bytes), one first item per selected store/department. Every
field, including all 1,941 daily values, was matched against the original CSV
using a streaming audit. The sample is kept locally, Git-ignored and not
distributed. Tracked sample provenance metadata records the source checksum.

Input structure and hashes were checked using streaming reads before profiling.
The existing profiler completed without a memory failure, so no implementation
refactor was made. An independent process observation recorded a 1,229.2 MiB
peak working set; the initial measurement helper tracked only the virtualenv
redirector, so its smaller peak value is not a valid pipeline memory estimate.

All raw files and real row-level samples remain Git-ignored. The manifest,
configuration, aggregate findings and metadata-only sample provenance remain
versioned. Redistribution rights have not been explicitly verified, so real
M5 row-level data is not distributed. Synthetic fixtures under `tests/fixtures/`
remain available for reproducible tests. M5 has no actual inventory observations.
Zero sales are not evidence of stockouts or zero demand.
