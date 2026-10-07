# Target architecture

Public CSV → Python → Bronze/Silver/Gold → DuckDB → Power BI

Python prepares public data in raw, cleaned and analytical layers. DuckDB
provides the canonical business metrics and queries. Power BI remains a future
consumer; it is not implemented in this sprint.

RP-01 established the repository, environment and standards. RP-02 through
RP-06 now provide local source inspection, Parquet Bronze snapshots, pandas
Silver transformations, DuckDB Gold marts and chronological forecasting
baselines. These stages are now validated on the real M5 pilot (3 stores ×
2 departments), with 3,575,322 daily rows and 4,530,250 reconciled units.
Synthetic regression fixtures remain independent of the real dataset.

Bronze → Silver identity links and checksums make source changes traceable.
Failed quality checks prevent publication. Gold owns metric definitions for
future BI/API/agent consumers; baseline outputs share its forecast schema.

Advanced ML, API, agent and AWS will be introduced in later stages. Early CI
checks lint and tests with repository fixtures; this does not complete RP-11.
