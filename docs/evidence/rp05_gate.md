# RP-05 real-data gate — 2026-10-07

Status: **REAL-DATA VALIDATED — PASS**.

Executed `python -m retailpulse gold --as-of 2026-10-07` in 73.076 seconds.
Gold run ID: `20f4dae75fff8e79204e`. Database:
`data/processed/gold/retailpulse.duckdb` (ignored).

| Entity | Rows | Unit total |
| --- | ---: | ---: |
| Selected wide Bronze | 1,842 series | 4,530,250 |
| fact_sales_daily (Silver and Gold copy) | 3,575,322 | 4,530,250 |
| mart_sales_daily | 3,575,322 | 4,530,250 |
| mart_store_weekly | 1,668 | 4,530,250 |
| mart_demand_alerts | 380,925 | Not an additive unit-total source |

Independent audits found zero duplicate daily or weekly keys and zero metric
mismatches. Revenue multiplication was checked across every daily row. Rolling
means were recomputed with calendar RANGE windows ending yesterday, independent
of the implementation's ROWS windows. Price changes were checked against a
previous-date self-join; the spike rule was independently recomputed against
the prior 28-day mean. No future dates enter either rolling calculation.
The checked-in SQL quality query returned no failures.

`data_freshness` is 3,790 days, from observed sales ending 2016-05-22 to explicit
as_of 2026-10-07. Source ingestion was `2026-10-07T21:29:04.505820+00:00`;
Gold was generated at `2026-10-07T21:33:38.610052+00:00`. These are distinct
concepts: running the pipeline today does not make historical sales current.

Missing-price rows remain 977,382. Under the documented conservative rule,
1,383 of 1,668 weekly rows have NULL canonical revenue_proxy. The known-price
partial sum is approximately 13,500,903.56; it is not audited revenue and is not
presented as a complete accounting total. Spike/event associations are noncausal.

All five CLI business queries completed. Before RP-06, query 03 returned its
header with zero observations as expected. It is rerun after real baseline
persistence. Representative outputs and forecast metrics are in the final
report and compact evidence files, not full generated-table exports.

Sampled process-tree peak was 3,260.63 MiB; an independent process observation
saw 4,070.6 MiB peak. Minimum sampled available system memory was 749.70 MiB;
the supervisor threshold was crossed near completion, but the CLI returned
exit 0 and the complete database passed independent audits. No metric formula
or implementation was changed to force a pass.
