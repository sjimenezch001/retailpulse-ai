# RP-05 gate — 2026-10-07

Status: CODE COMPLETE; REAL-DATA VALIDATION PENDING.

DuckDB materializes validated Silver entities, `mart_sales_daily` and
`mart_store_weekly`. SQL is the canonical metric implementation. The catalog
specifies definition, grain, filters, incomplete price handling and snapshot
freshness. `revenue_proxy` is explicitly a proxy, not audited revenue. Rolling
means exclude the current day; spikes have a documented noncausal threshold.
`fact_forecast` and `forecast_evaluation` are typed empty interfaces for RP-06;
`mart_demand_alerts` exposes the spike rule as a view.

Five numbered business queries execute reproducibly. Forecast errors are empty
until RP-06 supplies observations, rather than fabricated. Calendar events,
price associations, segment changes and metric provenance are queryable.

`python -m pytest -p no:cacheprovider`: `36 passed in 4.52s`.
`python -m ruff check .`: `All checks passed!`.
Synthetic checks reconcile Bronze → Silver → daily Gold → weekly Gold units,
retain missing prices, verify window boundaries and prove future mutations do
not affect earlier metrics. Invalid windows and tampered totals fail checks.
Identical Gold reruns preserve the database; changed source/SQL/as_of replaces
it and requires downstream forecast regeneration. No dependencies changed.

No real M5 data was available. Real totals, query results, performance and all
real-data gates remain pending. No production or real-data quality is claimed.
