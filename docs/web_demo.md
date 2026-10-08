# RetailPulse AI web demo

The RP-10 demo presents historical retail demand, frozen forecast evaluations
and answers grounded in approved tools. It adds FastAPI and Streamlit consumers
to the existing analytical core. It does not regenerate Gold or train a model.

## Install and launch (PowerShell)

From a fresh clone, use Python 3.12 (validated with 3.12.10) and create a new
virtual environment. The portable first run needs no M5, Ollama or training.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe scripts/tasks.py setup
.\.venv\Scripts\python.exe -m retailpulse demo --mode synthetic --provider deterministic
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
portable startup is `python -m retailpulse demo --mode synthetic --provider deterministic`.

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

## Real-data build and entry points

Existing Gold needs only `python -m retailpulse demo --mode real --provider deterministic`
from the activated environment. Use `--provider ollama` only when the optional
local service/model is installed and running. No real pipeline command was run
during RP-13 packaging.

For a new local real-data environment, obtain the three CSVs following
[source acquisition](data_source.md), accept the applicable competition terms,
and place them under `data/raw/m5/`. Then, from an activated environment:

```powershell
python -m retailpulse profile --select-pilot --sample
python -m retailpulse bronze
python -m retailpulse silver
python -m retailpulse gold --as-of 2026-10-07
python -m retailpulse baseline
python -m retailpulse model --validation-only
python -m retailpulse model
python -m retailpulse demo --mode real --provider deterministic
```

These are explicit build operations, not prerequisites for the synthetic demo.
They create local data and models; do not rerun them to present an existing frozen
installation. The [modeling protocol](modeling.md) explains frozen plan reuse.
For Power BI, run `python -m retailpulse export-bi` and
`python dashboards/powerbi/prepare_desktop.py`, then follow the
[Desktop build guide](../dashboards/powerbi/BUILD_GUIDE.md). Data-filled PBIX remains
local. [API examples](api_examples.md) and [assistant CLI](agent_demo.md) expose
the same analytical definitions.

## 150-second product walkthrough

| Time | Action and narration |
|---|---|
| 0–20 s | Overview, real historical mode: introduce the personal portfolio and commercial/BI/planning decisions. State that these are historical sales, not a customer deployment. |
| 20–45 s | Architecture: trace M5 → Bronze → Silver → Gold/DuckDB, then frozen forecasting/MLflow, Power BI and approved tools → API/UI. Explain lineage and the read-only serving boundary. |
| 45–80 s | Overview: show 4,530,250 observed units and source scope; select CA_1 to show 1,477,827, then reset All stores. Point out missing prices and partial revenue. |
| 80–105 s | Forecast, full-pilot test, both models: WMAPE 74.825958% vs 79.482353%; MAE improves but RMSE worsens, 2.431177 vs 2.361194. This is a backtest, not measured revenue uplift. |
| 105–135 s | Ask RetailPulse: use explicit deterministic mode and submit “How many units did CA_1 sell during April 2016?” Show 25,307, period, grounding, source and offline provider. Explain that the optional model confirms scope; tools supply figures. |
| 135–150 s | Architecture/limitations: point to recorded Windows/Linux/Docker evidence, 254 tests and 88.15% coverage; close with historical-data, inventory, bounded-assistant and deferred-AWS limitations. |

The shot list and [English SRT captions](demo_captions.en.srt) are the canonical
150-second sequence. Captions describe genuine actions and preserve the actual
provider. The [RP-13 gate](evidence/rp13_gate.md) records whether a finished video
was produced, its measured duration and local ignored path. No personal voice is
synthesized. A screenshot gallery is not a completed recording.

The completed local recording uses deterministic mode, so no model warm-up or
live-model claim is involved. Its measured encoded duration is 147.517067 seconds;
the capture schedule and script span 150 seconds. For a separate live variant,
first check `/health` and record
any warm-up used with the existing Ollama model. Preserve the measured response
latency and provider label; edited video duration is not inference latency. A
fallback cannot be represented as successful live-model validation.

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
