# RetailPulse AI — Locked MVP scope

## MUST

- M5 dataset with a configurable subset of 3 stores × 2 departments.
- Reproducible batch ingestion.
- Bronze / Silver / Gold.
- Data validations and tests.
- KPIs: units, revenue_proxy, rolling_7d, rolling_28d, price_change_pct, demand_spike_flag, data_freshness.
- SQL / DuckDB as the local analytics layer.
- Time-series baseline and candidate forecasting model.
- WMAPE as the primary metric; MAE/RMSE as supplementary metrics.
- Power BI with 3 pages.
- FastAPI.
- Assistant with get_kpi, get_forecast and search_metric_docs.
- Docker/reproducible environment for the consolidated release.
- README, evidence and demo.

## SHOULD

- PySpark / Databricks Free Edition as additional evidence.
- MLflow.
- Streamlit.
- Evaluation of 25 assistant questions.
- Structured logging.
- README.pt-BR.

## COULD

- Temporary AWS deployment: S3 + Glue/Athena + Lambda/API Gateway.
- IaC.
- Bedrock adapter.
- Simulated replenishment scenario.

## NOT NOW

- Kafka / streaming.
- Kubernetes.
- Deep learning.
- Redshift.
- Persistent RDS.
- Multiple microservices.
- Real-time data.
- Training a custom LLM.
- Production SLA.
- Personal data.

## Scope control rule
Any new idea is recorded in the backlog and does not change the MUST items until the release-ready MVP is finalized.
