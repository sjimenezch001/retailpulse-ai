# RetailPulse AI — Alcance congelado del MVP

## MUST
- Dataset M5 con subset configurable de 3 tiendas × 2 departamentos.
- Ingesta batch reproducible.
- Bronze / Silver / Gold.
- Validaciones y pruebas de datos.
- KPIs: units, revenue_proxy, rolling_7d, rolling_28d, price_change_pct, demand_spike_flag, data_freshness.
- SQL / DuckDB como capa analítica local.
- Baseline temporal y modelo candidato de forecasting.
- WMAPE como métrica principal; MAE/RMSE complementarias.
- Power BI con 3 páginas.
- FastAPI.
- Asistente con get_kpi, get_forecast y search_metric_docs.
- Docker/entorno reproducible para la versión consolidada.
- README, evidencias y demo.

## SHOULD
- PySpark / Databricks Free Edition como evidencia adicional.
- MLflow.
- Streamlit.
- Evaluación de 25 preguntas del asistente.
- Logging estructurado.
- README.pt-BR.

## COULD
- AWS temporal: S3 + Glue/Athena + Lambda/API Gateway.
- IaC.
- Adaptador Bedrock.
- Escenario de reposición simulado.

## NO AHORA
- Kafka / streaming.
- Kubernetes.
- Deep learning.
- Redshift.
- RDS persistente.
- Microservicios múltiples.
- Datos en tiempo real.
- Entrenar un LLM propio.
- SLA de producción.
- Datos personales.

## Regla anti-scope-creep
Cualquier idea nueva se registra en backlog y no modifica los MUST hasta cerrar la versión publicable del MVP.
