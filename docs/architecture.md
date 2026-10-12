# Implemented architecture

RetailPulse AI is a local Python application. pandas and PyArrow prepare the data;
DuckDB owns analytical definitions. Power BI, approved assistant tools and the web
demo consume those definitions. LightGBM and local MLflow/SQLite implement the
frozen forecasting experiment. RP-00 through RP-11 are implemented. A separate
RP-12D AWS demonstration now has genuine Glue 5.0 Spark and Athena reconciliation
evidence using synthetic data. It does not move historical M5/Gold or frozen
models into AWS. PostgreSQL and MinIO are not deployed.

## Build time and serving time

```mermaid
flowchart TB
  subgraph BUILD[Explicit local build operations]
    M5[M5 CSVs / local only] --> P[Profile / contracts / hashes]
    P --> B[Bronze / immutable Parquet runs]
    B --> S[Silver / pandas transformations and quality checks]
    S --> G[Gold / DuckDB marts and dimensions]
    G --> F[Fixed-origin baselines and LightGBM]
    F --> ML[MLflow / local SQLite and ignored artifacts]
    F -->|validated frozen forecasts| G
    G --> X[Reconciled BI export / local CSVs]
    X --> BI[Power BI / PBIP import model]
  end
  subgraph SERVE[Read-only analytical serving]
    G --> T[Approved Gold tools / parameterized SQL]
    Q[Question] --> R[Bounded router / validated scope]
    R --> O[Optional Ollama / structured confirmation]
    R --> A[Assistant orchestrator]
    O -->|exact scope equality required| A
    A --> T
    D[Approved local metric documents] --> A
    T --> API[FastAPI / typed responses and safe errors]
    A --> API
    API --> UI[Streamlit / deterministic presentation]
  end
  SYN[Packaged synthetic CSVs / checksum verified] --> SG[Separate disposable synthetic DuckDB]
  SG -->|explicit synthetic mode only| T
```

Build commands may publish data and frozen results. Starting the demo does not
run these commands. It queries existing real Gold read-only, or loads a separate
synthetic package snapshot when explicitly requested. Missing real Gold never
triggers synthetic substitution. See [source acquisition](data_source.md),
[modeling protocol](modeling.md) and [web modes](web_demo.md).

## Compact data and model map

```mermaid
flowchart LR
  DS[dim_store / store_id] --> SALES[mart_sales_daily / date + store_id + item_id]
  DP[dim_product / item_id] --> SALES
  DS --> FC[fact_forecast / model + split + origin + target + store + item]
  DP --> FC
  FC --> EV[forecast_evaluation / model + split + segment type + segment]
  RUN[Pipeline and model-run metadata] -. lineage .-> SALES
  RUN -. frozen provenance .-> FC
```

The diagram summarizes analytical grains, not every physical column. Sales facts
are not directly joined to forecast facts in the BI model. Power BI uses separate
daily and product-week facts and time dimensions, with dimension-to-fact filters.
WMAPE is `sum(abs(actual - predicted)) / sum(actual)`; it is not an average of
row percentages. RMSE derives from summed squared errors and observation counts.
Missing-price revenue stays explicitly partial or unknown. The
[metric catalog](metric_catalog.md), [dictionary](data_dictionary.md),
[Gold SQL](../sql/gold) and [BI model guide](../dashboards/powerbi/dashboard_spec.md)
are the detailed contracts.

## Forecasting boundary

Validation selects among three predeclared candidates. The design and final model
are frozen before the one-time test evaluation. All targets at an origin use only
history available at that origin; recursive horizons reuse predictions, not
held-out actuals. Historical LightGBM output and baseline forecasts coexist without
replacing each other. The [model card](model_card.md) records improved WMAPE/MAE
alongside worse RMSE. No future operational LightGBM service or replenishment
policy is implemented. Native models and MLflow data stay local and ignored.

## Assistant and API boundary

The deterministic router establishes supported intent and validates scope first.
Optional loopback-only Ollama confirms a closed structured selection that must
match that scope exactly. It does not create SQL, calculate the answer or expand
the supported grammar. The only tools are `get_kpi`, `get_forecast` and
`search_metric_docs`. Fixed SQL templates bind validated values as parameters.
DuckDB is read-only, external access and extension loading are disabled, and
time, memory and result sizes are bounded. Document retrieval cites a fixed local
corpus. Tools retrieve the figures; deterministic CLI/UI rendering presents them.

Preflight refusals and clarifications do not call the model. A validated selection
reports `ollama:qwen2.5:1.5b`; fallback is labeled separately and cannot count as
successful live validation. Questions are stateless. RP-10 adds bounded Spanish
normalization at the API boundary; it is not general multilingual conversation.
See [assistant safety](agent_safety.md), [orchestrator](../src/retailpulse/agent/orchestrator.py)
and [provider validation](../src/retailpulse/agent/provider.py).

FastAPI exposes `/health`, `/ready`, `/metrics/summary`, `/forecast` and
`/assistant/query`. Streamlit consumes the API; it does not calculate replacement
business metrics. The launcher owns its two servers and binds them to loopback.
Language and theme choices are session-local. Neither the application nor its
synthetic-only non-root container is an authenticated public production service.

## Engineering and evidence

Checksum-protected CSVs have explicit Git byte-preservation rules. The scanner
runs in UTF-8 on both platforms with exact reviewed exceptions. Regression,
coverage, dependency and secret checks fail closed. The
[RP-11 closure](evidence/rp11_gate.md#verified-closure--2026-10-08) links successful
Windows/Linux/Docker runs and the active main ruleset. The
[current published CI](https://github.com/sjimenezch001/retailpulse-ai/actions/runs/38265271761)
passed Windows, Ubuntu, container and aws-offline at `7eeb8e4` after PR #16
published RP-12D/RP-13. Structured logs
contain allowlisted operational metadata, not raw questions or provider bodies.

Use the [portfolio evidence index](portfolio_evidence.md) for genuine screenshots,
measured results and the distinction between historical real data, simulated
portable forecasts and actual live-model validation.

## Verified AWS laboratory — separate synthetic data path

The optional implementation under `cloud/aws/` and `infra/aws/` was exercised on
real AWS services on 2026-10-11. The local architecture above is unchanged.

```mermaid
flowchart LR
    Synthetic[Checksum-verified synthetic CSVs] --> S3[Private versioned S3 input]
    S3 --> Glue[Glue 5.0 Spark / two G.1X workers]
    Glue --> Curated[Versioned Parquet]
    Curated --> Catalog[Glue Data Catalog]
    Catalog --> Athena[Athena engine 3 / six fixed SELECTs]
    Athena --> Evidence[Recorded actual results / six PASS]
```

The successful Glue run produced five Parquet datasets and `_complete.json` /
`_metric_candidate.json`. All actual rows and marker values matched immutable
synthetic references. Six real Athena queries then validated 252 facts, 1,386
units, three store totals, 42 dates, dimension joins and quality/null semantics.
Athena reported 3,165 scanned bytes across the six queries; usage telemetry is
not the AWS invoice. The [live evidence](aws_live_demo.md) retains execution IDs
and separates actual engine runtime from launcher polling latency.

At execution time, seven workload resources were Terraform-tracked: workgroup, database and five
tables. The Glue job was created directly with Boto3 and the two STANDARD,
seven-day CloudWatch groups manually in Console. All ten were verified in the
recorded execution; a fresh inventory was not performed for this offline update.
The owner-managed private bucket, bounded execution role and IAM policies are
separate foundations. This is not a fully Terraform-managed deployment.

The first Glue runtime failure was resolved by removing ZIP-packaged SDK modules
and using Glue's built-in dependencies; the original bundle and S3 version were
retained. Athena response comparisons now accept only the observed final `;\n`
omission and the two exact default-catalog spellings. Outgoing SQL remains byte
exact and all account/database/workgroup/path/security limits remain enforced.

No `serving/` metric publication, Lambda, API Gateway, Bedrock, Redshift, cloud
forecasting or protected M5/model upload occurred. This diagram records the
demonstrated architecture, not a currently running cloud deployment.

The [final teardown](aws_teardown_report.md) records the job deletion, Athena
removal, six Catalog deletes and 27 exact S3 version deletes. Local Terraform
state is serial 31 with zero managed resources. The owner subsequently confirmed
the bucket, Glue role and unused boundary removal and final CloudWatch absence;
the cause of that absence is unverified. Selected CloudWatch evidence was
preserved, with explicit non-retention of other messages. Operator/bootstrap IAM
resources remain intentionally retained. Gross costs and final settled billing
remain unverified; estimated payable with credits is not gross consumption.
See the [final gate](evidence/rp12d_teardown_gate.md). Earlier RP-12A/C and
[RP-12D execution](evidence/rp12d_gate.md) documents and the
[original cleanup proposal](aws_cleanup_plan.md) remain dated historical evidence.
