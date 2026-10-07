# RP-04 real-data gate — 2026-10-07

Status: **REAL-DATA VALIDATED — PASS**.

Executed `python -m retailpulse silver` for `CA_1`, `CA_2`, `CA_3` ×
`FOODS_1`, `FOODS_2`. Runtime: 79.778 seconds. Silver run:
`3bb14677a2a3a1205013`; parent Bronze: `47b8b962c868f3c60fc8`.

| Output / measure | Actual value |
| --- | ---: |
| Selected item/store series | 1,842 |
| Distinct items | 614 |
| Observed dates | 1,941 |
| fact_sales_daily | 3,575,322 rows |
| dim_calendar | 1,969 rows |
| dim_product | 614 rows |
| dim_store | 3 rows |
| Total units | 4,530,250 |
| Missing-price rows | 977,382 (27.336894%) |
| Positive-unit rows with missing prices | 0 |

Daily fact dates span 2011-01-29–2016-05-22; the calendar includes the future
28 days through 2016-06-19. Dates are typed timestamps and units are int64,
nonnegative, non-null integers (pilot bounds 0–157).

Independent SQL audits found zero duplicate date/store/item keys, invalid
calendar mappings, invalid product/department/category mappings, invalid store
mappings, incorrect price joins or incorrect Bronze run IDs. Prices were checked
on the explicit store/item/retail-week keys, including NULL equality and the
`price_missing` flag. Every missing-price row is retained and has zero observed
units; this does not establish availability, inventory or stockout status.

Counts equal 1,842 × 1,941. A separate scan of the selected wide Bronze rows
reconciled all 4,530,250 units; per-series values also matched independently at
`d_1`, `d_7`, `d_365`, `d_1000`, `d_1941`. Existing fail-fast quality and failed
publication regression tests remain part of the full suite.

Memory was tight: sampled process-tree peak 2,616.09 MiB, independent process
peak observation 3,439.6 MiB, minimum sampled system availability 750.90 MiB.
The supervisor's low-memory threshold was crossed near completion; the CLI
returned exit 0 with a complete published snapshot. Independent integrity and
quality audits passed. This is a resource limitation, not a suppressed quality
failure; no Silver implementation change was required. Run stages serially.
