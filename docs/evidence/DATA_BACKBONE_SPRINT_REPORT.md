# Data Backbone Sprint Report

Date: 2026-10-07 (America/Sao_Paulo)
Branch: `feat/data-backbone`
Baseline: `826865e` — merged PR #5, synchronized from `origin/main`.

## Outcome and evidence boundary

RP-02 through RP-06 are CODE COMPLETE and locally validated with synthetic
fixtures. Every stage is REAL-DATA VALIDATION PENDING. No real M5 source files
were detected under the configured `data/raw/m5/` at pre-flight or final review.
No real-data gate passed, no real forecast metrics were measured, and no real
pilot ingestion, transformation or forecasting execution is claimed.

The acquisition manifest remains explicitly pending. Pilot store/department
lists remain empty. `data/sample/` contains only its placeholder; fabricated
observations exist solely under `tests/fixtures/m5_synthetic/` and are labeled.
Automated pipelines write generated results only to temporary directories.

## Local commits

One implementation commit per stage, followed by the early CI commit:

```text
f470e36 feat: prepare RP-02 data acquisition and profiling
d66f142 feat: implement RP-03 Bronze ingestion
a5ea2d8 feat: implement RP-04 Silver transformations
e756048 feat: implement RP-05 Gold analytics layer
4df36e9 feat: implement RP-06 forecasting baselines
35f9aa4 ci: add early validation workflow
```

This report is recorded in the separate local documentation commit
`docs: record data backbone sprint results`; its hash is intentionally not
embedded in its own contents. Use `git log --oneline --decorate -10` to inspect
all seven sprint commits. None were pushed. No PR or GitHub issue was modified.
Old local branches were retained. `main` was only fast-forwarded to `origin/main`
before the working branch was created; implementation commits are on this branch.

## Stage gates

| Stage | Implementation status | Passed with synthetic fixtures | Real M5 status |
| --- | --- | --- | --- |
| RP-02 | CODE COMPLETE | Missing/invalid source handling, schema/profile reports, deterministic pilot, repeatable SHA-256 and price coverage | REAL-DATA VALIDATION PENDING |
| RP-03 | CODE COMPLETE | CSV→Parquet, input/output counts, metadata, unchanged rerun reuse, changed-source snapshots, corruption detection | REAL-DATA VALIDATION PENDING |
| RP-04 | CODE COMPLETE | Unique daily grain, nonnegative integer units, typed dates, domain/mapping/key validity, missing price retention, referential integrity | REAL-DATA VALIDATION PENDING |
| RP-05 | CODE COMPLETE | Canonical DuckDB metrics, past-only windows, Bronze→Silver→Gold totals, five business queries, forecast interface | REAL-DATA VALIDATION PENDING |
| RP-06 | CODE COMPLETE | Chronological splits, three reproducible baselines, zero-denominator WMAPE, MAE/RMSE, segmentation, leakage rejection, Gold outputs | REAL-DATA VALIDATION PENDING |
| Early CI | Configured; local checks passed | Full CLI pipeline, reruns and failures with temporary synthetic projects | Hosted GitHub Actions run pending; RP-11 remains incomplete |

Stage evidence: [RP-02](rp02_gate.md), [RP-03](rp03_gate.md),
[RP-04](rp04_gate.md), [RP-05](rp05_gate.md), [RP-06](rp06_gate.md),
[early CI](early_ci_gate.md).

## Exact validation results

All commands used the existing `.venv` interpreter, Python **3.12.10**.
No dependency versions changed; `pyproject.toml` and `requirements.txt` are
unchanged from the synchronized baseline. No additional environment was created.

| Command | Result |
| --- | --- |
| `python -m pytest` | `53 passed, 1 warning in 46.61s` (exit 0) |
| `python -m pytest -p no:cacheprovider` | `53 passed in 44.98s` (exit 0) |
| `python -m ruff check .` | `All checks passed!` (exit 0) |
| `python -m pip check` | `No broken requirements found.` (exit 0) |
| `git diff --check` | Exit 0; no whitespace errors |
| `git status` before this report | Clean on `feat/data-backbone` |
| Workflow YAML inspection | Parsed; Python 3.12, read-only contents permission, no data acquisition/secrets |
| Repository language scan | No Spanish text detected in reviewed source, tests, configuration and documentation |

The pytest warning is `PytestCacheWarning`: Windows denies writing the
pre-existing `.pytest_cache/v/cache` directory. It was present at pre-flight.
It does not skip or fail tests; disabling the optional cache provider produces
a warning-free run. ACLs and global configuration were not modified.
Git also reported normal local CRLF→LF normalization messages, not diff errors.

Coverage includes all stage APIs and the actual CLI commands, five SQL business
queries, immutable snapshot reruns, corrupt/invalid inputs, failed publication,
unit reconciliation, missing prices, rolling boundaries, future-mutation tests,
hand-calculated errors, temporal splits and persisted forecast reruns.

## Files added, modified and removed

Relative paths; `A` added, `M` modified, `D` removed. Removed files are `.gitkeep`
placeholders for directories that now contain real project files.

```text
A	.github/workflows/validate.yml
M	README.md
M	config/local.yaml
A	data/contracts/raw_manifest.json
M	docs/architecture.md
A	docs/baselines.md
A	docs/data_dictionary.md
A	docs/data_source.md
D	docs/evidence/.gitkeep
A	docs/evidence/early_ci_gate.md
A	docs/evidence/rp02_gate.md
A	docs/evidence/rp03_gate.md
A	docs/evidence/rp04_gate.md
A	docs/evidence/rp05_gate.md
A	docs/evidence/rp06_gate.md
A	docs/metric_catalog.md
D	notebooks/.gitkeep
A	notebooks/01_data_profile.ipynb
A	scripts/verify.py
D	sql/checks/.gitkeep
A	sql/checks/gold_quality.sql
D	sql/gold/.gitkeep
A	sql/gold/interfaces.sql
A	sql/gold/mart_sales_daily.sql
A	sql/gold/mart_store_weekly.sql
A	sql/queries/01_sales_trend.sql
A	sql/queries/02_segment_changes.sql
A	sql/queries/03_forecast_errors.sql
A	sql/queries/04_events_and_prices.sql
A	sql/queries/05_metric_provenance.sql
A	src/retailpulse/__main__.py
A	src/retailpulse/data/__init__.py
A	src/retailpulse/data/config.py
A	src/retailpulse/data/snapshots.py
A	src/retailpulse/data/source.py
A	src/retailpulse/ingestion/bronze.py
A	src/retailpulse/models/baseline.py
A	src/retailpulse/models/metrics.py
A	src/retailpulse/quality/checks.py
A	src/retailpulse/transforms/gold.py
A	src/retailpulse/transforms/silver.py
A	tests/conftest.py
A	tests/data/test_source.py
A	tests/fixtures/README.md
A	tests/fixtures/m5_synthetic/calendar.csv
A	tests/fixtures/m5_synthetic/sales_train_evaluation.csv
A	tests/fixtures/m5_synthetic/sell_prices.csv
D	tests/integration/.gitkeep
A	tests/integration/test_baseline_pipeline.py
A	tests/integration/test_cli.py
A	tests/integration/test_ingestion.py
A	tests/integration/test_silver_pipeline.py
A	tests/sql/test_gold.py
D	tests/unit/.gitkeep
A	tests/unit/test_baseline.py
A	tests/unit/test_silver.py
A	docs/evidence/DATA_BACKBONE_SPRINT_REPORT.md
```

## Pending work and operational limits

- Obtain the real M5 files from the official competition and validate the
  manifest, actual schemas, checksums, row counts and quality findings.
- Derive the real 3-store/2-department pilot and sample, then execute the stages
  below. Reconcile real totals and replace pending gate claims with actual evidence.
- Evaluate real baselines; the synthetic tests do not establish model quality.
- Verify full-file and pilot runtime/memory on the local machine. Profiling and
  ingestion load sources in memory; Silver expands only the selected pilot.
- Snapshot publication and DuckDB writes assume one local pipeline writer.
  Unchanged outputs are reused; changed Gold generations invalidate forecasts
  and require a new baseline run. Historical Bronze/Silver snapshots are retained.
- Hosted Linux CI has not run because the branch has not been pushed. A remote
  check requires the user's later publication decision.
- The optional local pytest cache permission issue remains; the cache-disabled
  command is available without changing global settings.

M5 contains no actual inventory. Missing prices remain explicit, and
`revenue_proxy` is never audited revenue. Spike/event associations are noncausal.
Power BI, advanced ML/RP-07, API, agents, AWS, Ollama, Streamlit, PySpark and Docker
were not started. Early CI does not claim RP-11 completion.

## Next human step — real-data validation

From the repository root in PowerShell, follow [data source instructions](../data_source.md):
sign in to the official Kaggle competition, accept applicable rules and extract
`calendar.csv`, `sell_prices.csv`, `sales_train_evaluation.csv` into `data/raw/m5/`.
`sales_train_validation.csv` is not required. Do not commit the full inputs.

```powershell
.\.venv\Scripts\python.exe -m retailpulse profile --select-pilot --sample
.\.venv\Scripts\python.exe -m retailpulse bronze
.\.venv\Scripts\python.exe -m retailpulse silver
.\.venv\Scripts\python.exe -m retailpulse gold --as-of 2026-10-07
.\.venv\Scripts\python.exe -m retailpulse baseline
.\.venv\Scripts\python.exe -m retailpulse query 01_sales_trend
.\.venv\Scripts\python.exe -m retailpulse query 02_segment_changes
.\.venv\Scripts\python.exe -m retailpulse query 03_forecast_errors
.\.venv\Scripts\python.exe -m retailpulse query 04_events_and_prices
.\.venv\Scripts\python.exe -m retailpulse query 05_metric_provenance
.\.venv\Scripts\python.exe scripts/verify.py
git diff --check
git status
git log --oneline --decorate -10
```

The fixed `as_of` date above reproduces sprint-date freshness; choose a later
explicit date to measure recency as of another day. Review generated manifests,
source lineage, reconciliation summaries, Gold queries and baseline holdout
boundaries before updating real-data gate evidence. Keep all full/generated
data ignored. No push, merge, PR creation or issue mutation is part of this delivery.
