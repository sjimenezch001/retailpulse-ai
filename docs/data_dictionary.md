# Local data dictionary

| Layer / entity | Grain / keys | Main fields and contracts |
| --- | --- | --- |
| Bronze calendar | source row; `d` | All original source fields plus technical metadata |
| Bronze prices | source row; store/item/retail week | All original source fields plus technical metadata |
| Bronze sales | source row; store/item | Wide daily units; all source fields preserved |
| dim_calendar | `date` and `d` unique | Typed date, `wm_yr_wk`, original calendar event/SNAP fields when provided |
| dim_product | `item_id` | One `dept_id`, `cat_id` per item |
| dim_store | `store_id` | One `state_id` per store |
| fact_sales_daily | `date`, `store_id`, `item_id` | `units` integer >= 0, nullable positive `sell_price`, boolean `price_missing`; department/category/state, day/week and source lineage |
| mart_sales_daily | same daily key | All Silver fact fields plus seven canonical metrics |
| mart_store_weekly | `store_id`, `dept_id`, `wm_yr_wk` | Unit and proxy totals, coverage, observed period and day count |
| fact_forecast | origin/target/store/item/model/split | Predicted/actual units, horizon, department, demand level, training dates, source run ID; RP-06 populates it |
| forecast_evaluation | split/model/segment type/segment | WMAPE, MAE, RMSE, observation count, zero-denominator flag and source run ID; RP-06 populates it |
| mart_demand_alerts | daily sales key | View of explicit demand spike flags; not causal or inventory alerts |
| baseline_run | one active baseline evaluation | Exact holdout/training boundaries, model parameters, version and timestamp |
| metric_definitions | metric name | Canonical definition, grain and filter rules |
| pipeline_metadata | one active Gold generation | Bronze/Silver/Gold run IDs, source ingestion timestamp, sales range, as_of date and generation timestamp |

Bronze row metadata: `ingestion_ts` is the UTC ingestion time, `source_file` is
the original basename, `source_checksum` is SHA-256, and `pipeline_run_id` is the
content-derived Bronze run ID. Silver and daily Gold retain the sales source
lineage; the referenced Bronze summary identifies calendar/price sources too.
Derived Parquet snapshots include row counts, checksums and upstream identity.

Gold is `data/processed/gold/retailpulse.duckdb`. It materializes validated Silver
entities and canonical marts. Rebuilding with identical source, SQL and as_of
preserves the database, including forecasts. A changed Gold generation replaces
it and invalidates previous forecasts; rerun RP-06 afterward. All generated data
is ignored by Git. Writes assume a single local pipeline process.

## Validated real M5 pilot — 2026-10-07

The source has 30,490 wide sales rows, 6,841,121 price rows and 1,969 calendar
rows. The selected 1,842 series (614 items × 3 stores, 2 departments) span 1,941
observed dates, 2011-01-29–2016-05-22. Silver contains 3,575,322 daily fact rows,
1,969 calendar rows, 614 product rows and 3 store rows. The calendar extends
28 days beyond observed sales to 2016-06-19.

Gold contains 3,575,322 daily rows and 1,668 weekly rows. Both reconcile to
4,530,250 selected Bronze units. There are 464,184 baseline forecast rows and
222 aggregate evaluation rows. Missing daily prices remain explicit on 977,382
rows. The schemas above remain unchanged after real-data validation; see the
[sprint report](evidence/DATA_BACKBONE_SPRINT_REPORT.md) for lineage and checks.
