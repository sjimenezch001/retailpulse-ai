# Target architecture

Public CSV → Python → Bronze/Silver/Gold → DuckDB → Power BI

Python will prepare public data in raw, cleaned and analytical layers.
DuckDB will support queries on the results, and Power BI will present
business metrics.

RP-01 only establishes the repository, environment and standards; this
flow is not yet implemented. ML, API, agent and AWS will be introduced
in later stages.
