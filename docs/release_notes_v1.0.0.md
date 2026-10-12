# RetailPulse AI v1.0.0 — Portfolio Release

**Portfolio release:** package metadata, Python runtime and API project
version are `1.0.0`. The [release checklist](release_checklist.md) records
verification and acceptance boundaries. See
[GitHub Releases](https://github.com/sjimenezch001/retailpulse-ai/releases)
for the current publication status.

## What this release delivers

RetailPulse AI connects historical retail demand to reproducible metrics and
reports. It supports questions about store and product demand, changes over
observed periods, data coverage and forecast reliability.

- Python/SQL Bronze/Silver/Gold processing with source contracts, quality gates,
  lineage and canonical DuckDB metrics.
- Three native Power BI pages: Executive Overview, Store & Product Diagnostics
  and Forecast Performance, consuming reconciled analytical exports.
- Fixed-origin forecasting with baselines, LightGBM, local MLflow and frozen
  evaluation. Model selection uses validation only.
- A local FastAPI/Streamlit application with English/Spanish presentation,
  light/dark themes and a bounded read-only assistant. Optional local Ollama
  confirms structured tool selection; deterministic mode needs no model download.
- A completed temporary S3/Glue 5.0 Spark/Data Catalog/Athena demonstration:
  five Parquet datasets and six reconciled SELECTs over 252 synthetic facts and
  1,386 units. [Execution and engineering lessons](aws_live_demo.md) and
  [teardown evidence](aws_teardown_report.md) remain distinct from the local M5 path.
- Original project code licensed under [MIT](../LICENSE). Third-party dependencies,
  external assets and M5 competition data retain separate permissions.

## Measured evidence

- [Historical pilot](evidence/rp09_real_acceptance.json): 4,530,250 observed units.
- [Frozen model](model_card.md): test WMAPE 74.825958% versus 79.482353% for
  rolling mean; MAE improves, RMSE worsens (2.431177 versus 2.361194).
- [Live assistant evaluation](evidence/rp09_live_evaluation.json): 36 expected
  outcomes, including 22 validated Ollama calls and 14 preflight outcomes,
  with zero fallback. This is a curated evaluation.
- [Published baseline CI](https://github.com/sjimenezch001/retailpulse-ai/actions/runs/38274725819):
  Windows, Ubuntu, container and aws-offline passed at `685839e7` after PRs #16
  and #17. This is not remote validation of the new release candidate.
- [Local candidate validation](release_checklist.md#local-candidate-validation):
  440 passing tests, 88.15% coverage, verified distributions and a clean installed
  deterministic demo. The checklist records the pre-existing global formatting result.

## Install and reproduce

Use Python 3.12 and the [portable quick start](../README.md#portable-quick-start).
The synthetic deterministic demo needs no M5 download, Ollama, training or AWS
account. SYN_A's example returns 378 synthetic units. Real-data builds and
Power BI refresh are documented in the [web guide](web_demo.md#real-data-build-and-entry-points)
and [Power BI build guide](../dashboards/powerbi/BUILD_GUIDE.md).

Distributions contain Python source and the packaged synthetic snapshot.
The repository also provides report definitions, screenshots and aggregate evidence.
Real M5 rows, populated databases, frozen models, data-filled PBIX and MP4s remain
local and excluded from distributions.

## Interpretation and acceptance

Historical sales do not measure inventory or establish causality or revenue
impact. Forecast gains are pilot-specific; simulated portable forecasts are
not trained-model evidence. The assistant is bounded and stateless, and the
application is local without public-service authentication. AWS billing and
CloudWatch history retain the precise evidence gaps in the teardown report.

The [release checklist](release_checklist.md) records release verification and
publication decisions. Independent human quick-start verification remains
**PENDING** and is not represented as a passing test. Public video hosting
and localized video review are separate optional presentation decisions.
