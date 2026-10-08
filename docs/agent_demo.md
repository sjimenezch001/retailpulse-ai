# Local grounded assistant demo

Use the existing Python 3.12 environment and canonical Gold database. Do not
rerun profiling, transformation, training or Power BI export for this demo.
Numerical answers need local `data/processed/gold/retailpulse.duckdb`;
documentation questions work without Gold. The public repository contains
synthetic fixtures and aggregate evidence, not real M5 observations.

## Commands

From the repository root in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m retailpulse ask "How many units did CA_1 sell during April 2016?"
.\.venv\Scripts\python.exe -m retailpulse ask "Compare units by department from 2016-04-25 to 2016-05-22 with the previous period"
.\.venv\Scripts\python.exe -m retailpulse ask "Compare LightGBM and rolling mean WMAPE on the test period"
.\.venv\Scripts\python.exe -m retailpulse ask "What does revenue_proxy mean?"
.\.venv\Scripts\python.exe -m retailpulse ask "How fresh is the data?"
.\.venv\Scripts\python.exe -m retailpulse ask "Do zero sales prove stockouts?"
.\.venv\Scripts\python.exe -m retailpulse ask "How many units did CA_1 sell today?"
.\.venv\Scripts\python.exe -m retailpulse agent-eval
```

Append `--provider deterministic` for offline execution without a provider
probe. Append `--json` to `ask` for the typed result. Configuration selection
uses `--config config/local.yaml` before the command. `ask` exits zero for
answered, clarification and refusal outcomes; inspect `status` to distinguish
them. It exits nonzero for unavailable/error outcomes. `agent-eval` exits
nonzero for any failed expected outcome or missing inputs.

## Measured real M5 results

Gold run `20f4dae75fff8e79204e` covers 2011-01-29 through 2016-05-22 and has
`as_of_date=2026-10-07`. Every result identifies this historical scope.

| Question | Independently reconciled result |
| --- | --- |
| CA_1 units, April 2016 | 25,307 units |
| Entire pilot, all observed dates | 4,530,250 units |
| FOODS_1, 2016-04-25–2016-05-22 versus preceding 28 days | 37,422 vs 30,820; +6,602 (+21.421155%) |
| FOODS_2, same intervals | 50,001 vs 48,499; +1,502 (+3.096971%) |
| LightGBM test | WMAPE 74.825958%; MAE 1.268324; RMSE 2.431177 |
| Rolling mean test | WMAPE 79.482353%; MAE 1.347252; RMSE 2.361194 |
| Snapshot freshness | 3,790 days |
| Inventory / today's sales | Explicit limitation; no invented value |

LightGBM's RMSE is worse than rolling mean's. These are frozen historical
backtests; the assistant does not retrain, select a new winner or claim
operational future LightGBM forecasts. Revenue explanations preserve the
difference between a complete proxy and a partial priced subset.

The [aggregate acceptance JSON](evidence/rp09_real_acceptance.json) records
six numerical examples, including store changes, with their provenance.
The [golden evaluation JSON](evidence/rp09_evaluation.json) records 36 passing
outcomes: 20 answers and 16 safe refusals/clarifications. All 16 numerical
cases reconcile independently and have source metadata. Runtime latencies
are local measurements, not a deployment performance guarantee.

## Supported scope

Use one approved KPI and one continuous interval: `from YYYY-MM-DD to
YYYY-MM-DD`, `on YYYY-MM-DD`, a full month name and year, or `all observed
dates`. Supply one store, department and/or item identifier. KPI grouping
supports day, Gold week, month, store or department. Units comparisons support
`previous period` at total/store/department grain. `data_freshness` is global.

Forecasts require explicit model names and `validation`, `test` or `future`.
Models are `last_value`, `rolling_mean`, `seasonal_naive_7` and
`lightgbm_global_v1`; common spaced names and `LightGBM` are understood.
Optional scope includes dates, a single `horizon N`, a named demand level,
store/department/item filters and grouping by day/store/department/horizon/
demand level. Requests exceeding 100 output groups ask for a narrower scope.

The assistant is stateless and supports conservative English patterns.
Spanish, conversational follow-ups, arbitrary rankings, inventory advice
and arbitrary query generation are not implemented. Ambiguous `sales`
requires choosing units or a revenue measure. Unsupported extra conditions
are not silently discarded.

## Ollama status and activation

On the validated machine, Ollama was absent from PATH and its standard local
installation path; the loopback model inventory did not respond. No model
was downloaded or executed. Default answers therefore identify
`deterministic_fallback:ollama_or_selected_model_unavailable`. Adapter tests
use mocks. **Live local LLM validation is pending.**

To complete it later, install/start Ollama and use an already installed model
shown by `ollama list`. If no suitable model exists, obtain the user's approval
for the download before installing one. This project performs no downloads.
Replace `INSTALLED_MODEL_NAME` with the exact installed model name:

```powershell
ollama list
.\.venv\Scripts\python.exe -m retailpulse ask "How many units did CA_1 sell during April 2016?" --provider ollama --ollama-model INSTALLED_MODEL_NAME
.\.venv\Scripts\python.exe -m retailpulse agent-eval --provider ollama --ollama-model INSTALLED_MODEL_NAME
```

Confirm supported answers actually report `ollama:INSTALLED_MODEL_NAME`,
and inspect each evaluation record's provider. Refused inputs are rejected
before any model call. An all-passing run that used fallback is valid
engineering evidence but does not complete live LLM validation. Record the
actual model, successful selections, grounded results and latency separately.
The adapter cannot change validated scope or supply figures.

## Reproducible evaluation

`tests/agent/golden_questions.yaml` fixes expected tool arguments and outcomes.
Dates and identifiers adapt to the selected snapshot. Synthetic tests build
their own temporary Gold, including the real schema's timestamp date type;
CI never needs real data or Ollama.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/agent -p no:cacheprovider
.\.venv\Scripts\python.exe -m retailpulse agent-eval --provider deterministic
```

The evaluator compares KPIs with independent Gold aggregate SQL and forecast
totals with `fact_forecast`; historical metrics also reconcile to
`forecast_evaluation`. It checks expected scope, periods, provenance, citations
and refusal categories. An answered-but-wrong number fails. Evaluation output
contains no raw observations and goes to `artifacts/agent/evaluation.json`.
Committed evidence is a reviewed snapshot; local runs do not overwrite it.
