# Canonical metric catalog

Gold is the canonical source for future BI, API and agent consumers. SQL under
`sql/gold/` owns calculations; `metric_definitions` exposes definitions, grain and
filter rules inside DuckDB. Do not independently recreate these metrics in clients.

| Metric | Definition | Grain and filters |
| --- | --- | --- |
| units | Observed nonnegative daily unit sales | date × store × item; additive; filter date, store, department, item |
| revenue_proxy | `units * sell_price`; unknown if price is missing | same grain; sum only with complete price coverage; a proxy, not audited revenue |
| rolling_7d | Mean units over previous 7 consecutive days, excluding today; NULL before 7 observations | same grain; calculate before filtering; not additive across dates |
| rolling_28d | Mean units over previous 28 consecutive days, excluding today; NULL before 28 observations | same grain; calculate before filtering; not additive across dates |
| price_change_pct | `100 * (sell_price - previous_day_price) / previous_day_price`; NULL if either price is missing or denominator is zero | same grain; no forward filling; not additive |
| demand_spike_flag | Current units strictly exceed twice the previous 28-day mean, with all 28 observations and positive mean; otherwise false | same grain; association/triage flag, never evidence of causality |
| data_freshness | Calendar days between maximum observed sales date and explicit `as_of` date | global dataset snapshot; unchanged by segment filters; historical M5 is intentionally old |

Rolling windows cannot look ahead. Silver guarantees consecutive daily rows;
Gold verifies continuity before using row-based SQL windows. All date bounds
are inclusive unless a query explicitly says otherwise. `--as-of YYYY-MM-DD`
makes freshness reproducible; by default it is the UTC execution date and must
not precede the latest sales date. This measures data recency, not pipeline latency.

`mart_store_weekly` groups by store, department and M5 `wm_yr_wk`, which is not
an ISO week number. Partial boundary weeks expose `observed_days`. Its canonical
`revenue_proxy` is NULL if any included daily price is missing. The separate
`known_revenue_proxy` is a partial sum and must never be presented as a complete
total; `missing_price_rows` and `price_coverage` expose this limitation.

## Reproducible business queries

Run any numbered SQL file in `sql/queries/` using `python -m retailpulse query NAME`:

1. `01_sales_trend`: units and revenue_proxy over observed dates.
2. `02_segment_changes`: last 7 versus previous 7 observed dates, store/department contributions.
3. `03_forecast_errors`: horizon forecasts and historical errors; empty until RP-06 runs.
4. `04_events_and_prices`: event/price associations, with no causality claim.
5. `05_metric_provenance`: definitions, period, source table and source/update lineage.

Query 2 requires at least 14 observed daily dates for two complete periods;
inspect the data range in query 5 before interpreting shorter samples.

## Real M5 pilot findings — 2026-10-07

The validated 3-store × 2-department pilot retains 977,382 missing-price rows
(27.336894% of 3,575,322 daily rows). All those rows have zero observed units;
prices remain NULL and the quality flag remains true. This does not establish
inventory availability. Under the existing conservative aggregation rule,
1,383 of 1,668 weekly rows have unknown canonical revenue_proxy. The known-price
partial sum is approximately 13,500,903.56 and is not audited revenue.

The documented spike rule flags 380,925 daily rows. These are heuristic review
signals, not confirmed demand events or causal conclusions. At `as_of = 2026-10-07`,
data_freshness is 3,790 days because the final sales date is 2016-05-22, despite
the pipeline being executed in 2026. Independent audits found no metric formula
mismatch; no canonical calculation was changed for these findings.
