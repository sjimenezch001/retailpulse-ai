# Target architecture

Public CSV → Python → Bronze/Silver/Gold → DuckDB → Power BI

Python prepares public data in raw, cleaned and analytical layers. DuckDB
provides the canonical business metrics and queries. RP-08 implements Power BI
as a local consumer through deterministic, reconciled CSV imports.

RP-01 established the repository, environment and standards. RP-02 through
RP-06 now provide local source inspection, Parquet Bronze snapshots, pandas
Silver transformations, DuckDB Gold marts and chronological forecasting
baselines. These stages are now validated on the real M5 pilot (3 stores ×
2 departments), with 3,575,322 daily rows and 4,530,250 reconciled units.
Synthetic regression fixtures remain independent of the real dataset.

Bronze → Silver identity links and checksums make source changes traceable.
Failed quality checks prevent publication. Gold owns metric definitions for
future BI/API/agent consumers; baseline outputs share its forecast schema.

RP-07 adds reusable past-only features, a global LightGBM model and local
MLflow/SQLite experiment tracking. Validation selects and freezes the design
before the one-time test evaluation. ML and baseline forecasts coexist in Gold;
real observations, model files and tracking artifacts remain local and ignored.
See the [model card](model_card.md) and [gate evidence](evidence/rp07_gate.md).

RP-08 adds `export-bi`: read-only Gold views produce daily store/department
summaries, observed-week product summaries, backtest observations and shared
dimensions. SQL checks run before export publication. Hashes, row counts and
lineage are recorded in a local manifest; exports stay under ignored artifacts.
Power Query's built-in CSV connector avoids a third-party DuckDB driver.

The versioned PBIP contains three native PBIR pages and a portable TMDL import
model. Its 14 relationships filter from dimensions toward facts. Facts never
join each other; daily and weekly grains use separate time dimensions. Explicit
DAX derives weighted forecast metrics from additive error components. An
intentionally disconnected model-comparison dimension replaces only the model
selector during baseline comparisons. No model retraining occurs in BI.

Desktop rendering, native interactions, 16 SQL-backed DAX checks, genuine
screenshots and a saved/reopened local PBIX passed. The configured local
project, caches and data-filled PBIX remain ignored. See the
[dashboard specification](../dashboards/powerbi/dashboard_spec.md) and
[RP-08 gate](evidence/rp08_gate.md).

API, agent and AWS remain future stages. Early CI checks lint and tests with
repository fixtures; this does not complete RP-11. RP-09 has not started.
