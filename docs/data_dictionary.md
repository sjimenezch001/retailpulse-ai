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
