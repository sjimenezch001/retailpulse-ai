# RetailPulse AI web demo

The RP-10 demo presents historical retail demand, frozen forecast evaluations
and answers grounded in approved tools. It adds FastAPI and Streamlit consumers
to the existing analytical core. It does not regenerate Gold or train a model.

## Install and launch (PowerShell)

From the repository root, use Python 3.12.10 and the existing virtual environment.
For a fresh clone, first create it with `py -3.12 -m venv .venv`.

```powershell
.\.venv\Scripts\python.exe scripts/tasks.py setup
# Existing local Gold and the optional installed Ollama model:
.\.venv\Scripts\python.exe -m retailpulse demo
```

Open **http://127.0.0.1:8501**. The API is **http://127.0.0.1:8000**;
interactive API documentation is **http://127.0.0.1:8000/docs**.
The launcher checks readiness and reports these URLs. Press **Ctrl+C** in its
terminal to stop both child servers. It uses the invoking virtual-environment
Python, reports occupied ports, and cleans up partial startup failures.

These commands need no real M5 download or model training:

```powershell
# Portable, fully offline business-question routing:
.\.venv\Scripts\python.exe -m retailpulse demo --mode synthetic --provider deterministic
# Real Gold with explicit deterministic routing selected in the UI:
.\.venv\Scripts\python.exe -m retailpulse demo --provider deterministic
# Run a second, isolated portable instance if desired:
.\.venv\Scripts\python.exe -m retailpulse demo --mode synthetic --provider deterministic --api-port 8001 --ui-port 8502
```

After activating `.\.venv\Scripts\Activate.ps1`, the equivalent one-command
startup is `python -m retailpulse demo`.

| Mode | Source and behavior |
|---|---|
| Real (default) | Existing local `data/processed/gold/retailpulse.duckdb`, read-only. Genuine historical lineage and frozen backtests. Missing Gold produces an explicit degraded screen with the synthetic launch command; no automatic substitution. |
| Synthetic | Six packaged CSV snapshots authored only from `tests/fixtures/m5_synthetic`. 252 daily observations, six series, 1,386 units, 2020-01-01–2020-02-11. UI and responses explicitly label them synthetic. An illustrative LightGBM-shaped series is simulated, not trained or claimed as model evidence. |

Synthetic startup only loads the snapshots into a disposable ignored DuckDB
database. It does not run ingestion, forecasting or training. The source builder
is `scripts/build_portable_demo.py`; repeated builds produce identical CSV bytes.
Synthetic metadata, dimension names and document retrieval remain separate from
real M5. Real samples, databases, models, traces and data-filled PBIX files remain
ignored. Only synthetic observations and aggregate real acceptance evidence are
distributed.

## What to show

The header provides session-persistent **English / Español** and **Light / Dark**
selectors. The visual refinement uses neutral light/charcoal surfaces, restrained
chart colors and local Segoe UI Variable / Segoe UI system fonts, inspired by
the typography and restrained presentation of [ElevenLabs](https://elevenlabs.io/).
No remote fonts, paid UI packages or external model services are loaded.
Dates use MM/DD/YYYY in English and DD/MM/YYYY in Spanish; explicit date fields
validate against the observed period. Numeric display uses the selected locale,
including chart axes and tooltips, without changing the underlying values.

Assistant cards now render the existing typed result: a short business sentence,
prominent value, period, filters, source and grounding status. Provider identity
and duration are secondary, while complete provenance and diagnostics remain
inside the details expander. Forecast comparisons and documentation have their
own structured views. Reviewed documentation translations are keyed to exact
source excerpts; unknown quotations retain their original English with an
explicit label, preserving genuine citations.

Spanish question support is deliberately bounded. The API recognizes four
intent families: store units for an explicit month/year or ISO interval,
LightGBM test WMAPE or comparison with rolling mean, the revenue_proxy definition,
and global data freshness. Full-string allowlist matches normalize into the
existing RP-09 router; extra conditions are never silently discarded. Unsupported
Spanish asks for clarification. English inputs and contracts are unchanged.
Example questions are localized in the UI. This is not unrestricted multilingual
conversation support. Theme/language choices do not rewrite configuration files
or affect another browser session.

- **Overview:** units, price coverage, partial known-price revenue, spike flags,
  exact snapshot freshness, daily trend and store/department comparisons. Date,
  store and department filters use API results. Daily chart spans at most 90 days;
  headline totals use the entire selected period.
- **Forecast:** test/validation split, model, store, department and exact horizon
  filters. WMAPE/MAE/RMSE and observed-versus-predicted daily totals stay separate
  for each model. Full-pilot test LightGBM improves WMAPE and MAE, but has worse
  RMSE than rolling mean. Segment results can differ. No future LightGBM claims.
- **Ask RetailPulse:** clickable examples, local Ollama/deterministic selector,
  answer, selected tool, grounding, dates, source and latency. A successful local
  model call is marked explicitly; deterministic fallback has a warning and never
  appears as live-model success. Each question is independent. Chat history is
  only presentation and is not supplied as conversational context.
- **Architecture:** source-to-answer flow, documentation links, reproducibility
  and limitations. No AWS or operational inventory deployment is claimed.

`3,790 days` is the real snapshot's freshness **at 2026-10-07**, not elapsed
pipeline processing time or a live value recalculated at browser launch.
M5 ends on 2016-05-22. Known-price revenue is not audited commercial revenue;
missing prices are not zero. Demand spikes are heuristic and do not prove causes
or stockouts.

## 150-second interview script

| Time | Action and narration |
|---|---|
| 0–20 s | Open Overview. “Retail teams need consistent demand definitions across stores. This product makes historical sales, forecasts and answers traceable to one analytical source.” Point out real or synthetic mode. |
| 20–50 s | Show units, price coverage and the missing-price notice. Change the store filter, follow the trend, open provenance. Explain the exact snapshot date and historical freshness. |
| 50–80 s | Open Forecast, test split, both models. “LightGBM improves WMAPE and MAE; rolling mean has lower RMSE. We retain that tradeoff rather than declaring an unconditional winner.” Show actuals and the two prediction series. |
| 80–120 s | Open Ask RetailPulse and click Explore store demand. During the local-model spinner, explain the fixed tool allowlist and strict validation. Show 25,307 CA_1 units for April 2016, grounding and the actual provider. If offline, choose deterministic and say so explicitly. |
| 120–150 s | Open Architecture. Trace M5 through Bronze/Silver/Gold to forecasting, BI and the application. Show lineage, mention synthetic regression tests, preserved model hashes and portable mode. End with historical-data and inventory limitations. |

For a predictable presentation, check `/health` first and submit one warm-up
question to load Ollama. Cold model loading may take much longer than a warm
call. A fallback remains useful but is not live LLM validation.

## Validation and troubleshooting

```powershell
.\.venv\Scripts\python.exe scripts/verify.py
# Opt-in real acceptance; the real demo and Ollama must already be running:
.\.venv\Scripts\python.exe scripts/check_web_api.py
# Actual browser acceptance using installed Chrome (optional browser tooling):
.\.venv\Scripts\python.exe scripts/check_web_browser.py --mode real --chrome 'C:\Program Files\Google\Chrome\Application\chrome.exe'
.\.venv\Scripts\python.exe scripts/check_web_browser.py --mode synthetic --port 8502 --chrome 'C:\Program Files\Google\Chrome\Application\chrome.exe'
```

The normal test suite uses synthetic fixtures and mocked provider discovery;
it needs neither Kaggle, Ollama nor a browser. Browser acceptance is opt-in and
uses Playwright from the optional `browser` extra (also pinned in the validated
development requirements). No browser binary is downloaded by the demo.

If Ollama is unavailable, start its local service with the installed
`qwen2.5:1.5b` model or select deterministic mode. If ports are occupied, stop the
earlier demo or choose alternative ports. On API failure the UI gives an actionable
message without exposing transport exceptions. Runtime logs and sanitized
assistant traces are local under `artifacts/web_demo/<mode>/`; these are ignored.
The source never reads credentials. Browser telemetry is disabled.

See [API contracts and examples](api_examples.md) and the
[RP-10 gate with actual screenshots](evidence/rp10_gate.md).
