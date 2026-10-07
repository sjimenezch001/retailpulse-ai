# Target architecture

Public CSV → Python → Bronze/Silver/Gold → DuckDB → Power BI

Python prepares public data in raw, cleaned and analytical layers. DuckDB
provides the canonical business metrics and queries. Power BI remains a future
consumer; it is not implemented in this sprint.

RP-01 established the repository, environment and standards. RP-02 through
RP-06 now provide local source inspection, Parquet Bronze snapshots, pandas
Silver transformations, DuckDB Gold marts and chronological forecasting
baselines. They are code complete and tested on synthetic fixtures only;
real M5 data validation is pending.

Bronze → Silver identity links and checksums make source changes traceable.
Failed quality checks prevent publication. Gold owns metric definitions for
future BI/API/agent consumers; baseline outputs share its forecast schema.

Advanced ML, API, agent and AWS will be introduced in later stages. Early CI
checks lint and tests with repository fixtures; this does not complete RP-11.
