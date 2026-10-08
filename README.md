# RetailPulse AI

Retail demand analytics platform. It turns historical sales, calendar data and
prices into verifiable business metrics for comparing stores and departments,
reducing fragmented analysis and inconsistent business definitions.

**Status: RP-10 engineering PASS; full gate PASS, including real browser and Ollama validation.**
FastAPI and Streamlit expose four endpoints and four portfolio tabs, with
separate real Gold and explicitly synthetic portable modes. See the
[web demo guide](docs/web_demo.md) and [RP-10 gate](docs/evidence/rp10_gate.md).

RP-09 engineering and full gate passed, including live Ollama validation.
RP-00–RP-08 remain validated. The local grounded assistant passes all 36
golden questions against synthetic and real M5 Gold. The strict live run with
Ollama 0.40.0 / `qwen2.5:1.5b` passed with 22 validated model calls, 14
preflight outcomes and zero fallback cases.
The frozen LightGBM model scores 74.825958% test WMAPE versus 79.482353% for
rolling mean; RMSE is worse (2.431177 versus 2.361194). Selection used validation
only. RP-00 and RP-01 are complete. Full inputs, forecasts, model files and
MLflow artifacts remain local and Git-ignored. RP-08 adds three native Power BI
pages, a reconciled serving layer and a validated local PBIX. The PBIX was saved
and reopened in Desktop; data-filled binaries and CSV exports remain ignored.
See the [dashboard gate and screenshots](docs/evidence/rp08_gate.md).

Stack: Python 3.12, pandas, PyArrow, DuckDB, Pydantic and PyYAML.
Modeling: LightGBM and local MLflow tracking with SQLite.
BI: Power BI Desktop, native PBIR reports and a TMDL import model.
Assistant: approved read-only Gold tools, deterministic document retrieval and
an optional loopback-only Ollama adapter; no additional dependencies.
Web demo: FastAPI, Uvicorn, Streamlit, HTTPX and Altair, bound to localhost.
Development: pytest and Ruff. Packaging: setuptools and pip.

## Repository structure

```text
config/local.yaml      Relative paths and the derived real M5 pilot
data/contracts/        Inspected source manifest with hashes and profiles
data/sample/           Local-only M5 samples; tracked guidance and provenance
notebooks/             Thin profiling notebook
sql/{silver,gold,bi,checks,queries}/
src/retailpulse/        data/, ingestion/, transforms/, quality/, features/, models/, bi/, agent/, api/
app/streamlit_app.py    Four-tab portfolio UI; consumes only the local API
src/retailpulse/api/synthetic/  Distribution-safe portable snapshots
tests/                 Synthetic fixtures, unit, integration and SQL checks
docs/                  Source, metrics, dictionary, baselines and gate evidence
traces/sample.json     Redacted illustrative assistant trace; runtime traces are ignored
dashboards/powerbi/     Portable PBIP/PBIR/TMDL, measures and reproducible build tools
scripts/verify.py      Local checks using the invoking Python environment
.github/workflows/     Early CI; no datasets or secrets required
pyproject.toml         Metadata, dependencies and tool configuration
requirements.txt       Exact versions from the validated environment
.env.example           Template without credentials
```

Raw and processed data, real M5 samples and generated artifacts are excluded from Git.
Real row-level samples are generated locally and are not distributed in the repository.
Synthetic source fixtures are under `tests/fixtures/`; derived portable snapshots
are packaged under `src/retailpulse/api/synthetic/`.

## Quick Start — Windows PowerShell

From the repository root, use Python 3.12 (validated with 3.12.10).
Reuse the existing `.venv`; only create one if absent with `py -3.12 -m venv .venv`.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pip check
```

Alternatively, `.\.venv\Scripts\python.exe scripts/verify.py` runs all local
checks. Tests require no real dataset, network access or credentials.
`pyproject.toml` is the primary configuration; `requirements.txt` pins runtime
and development dependencies. The project uses an editable `src/` installation.

## Local portfolio demo

```powershell
# Existing real Gold and local Ollama:
.\.venv\Scripts\python.exe -m retailpulse demo
# Portable demo without Kaggle or Ollama:
.\.venv\Scripts\python.exe -m retailpulse demo --mode synthetic --provider deterministic
```

Open <http://127.0.0.1:8501>; API docs are at <http://127.0.0.1:8000/docs>.
Press Ctrl+C to stop both servers. After activating the environment, the startup
command is `python -m retailpulse demo`. Missing real Gold is reported explicitly;
synthetic data is never silently substituted. See the [150-second demo script,
mode details and screenshots](docs/web_demo.md).

## Real-data pipeline

Follow [source acquisition instructions](docs/data_source.md) to obtain the three
official M5 CSVs and extract them into `data/raw/m5/`. Do not copy synthetic
fixtures there. Then run the stages in order:

```powershell
.\.venv\Scripts\python.exe -m retailpulse profile --select-pilot --sample
.\.venv\Scripts\python.exe -m retailpulse bronze
.\.venv\Scripts\python.exe -m retailpulse silver
.\.venv\Scripts\python.exe -m retailpulse gold
.\.venv\Scripts\python.exe -m retailpulse baseline
.\.venv\Scripts\python.exe -m retailpulse model --validation-only
.\.venv\Scripts\python.exe -m retailpulse model
.\.venv\Scripts\python.exe -m retailpulse query 01_sales_trend
.\.venv\Scripts\python.exe -m retailpulse query 03_forecast_errors
```

Profiling derived `CA_1`, `CA_2`, `CA_3` and `FOODS_1`, `FOODS_2` from the
real source identifiers. This pilot contains 614 items, 1,842 series and
3,575,322 daily rows. Missing inputs still produce a pending manifest and stop
downstream stages; tests remain independent of the local real data.
Configuration paths are relative to the repository root. Use
`--config config/local.yaml` before the subcommand to select configuration.
For reproducible freshness, use `gold --as-of YYYY-MM-DD` with a date no earlier
than the latest sales date. Baselines default to 28-day validation/test holdouts
and a 28-day future horizon, with visible training boundaries.
The model command compares three candidates on validation, freezes the winner,
and evaluates test once. Reruns reuse verified artifacts and preserve baseline
outputs. See the [modeling protocol](docs/modeling.md) for the immutable plan,
past-only features and interrupted-evaluation handling.

Read the [metric catalog](docs/metric_catalog.md), [data dictionary](docs/data_dictionary.md),
[baseline protocol](docs/baselines.md) and [sprint report](docs/evidence/DATA_BACKBONE_SPRINT_REPORT.md).
The [model card](docs/model_card.md) and [RP-07 gate](docs/evidence/rp07_gate.md)
record candidate selection, the final test, segment regressions and MLflow runs.
`revenue_proxy` is a proxy, not audited revenue; M5 provides no real inventory.
Early CI is a guardrail, not completion of RP-11.

## Local Power BI dashboard

With the existing RP-07 Gold database, export the BI data and configure an
ignored local project without rerunning earlier stages:

```powershell
.\.venv\Scripts\python.exe -m retailpulse export-bi
.\.venv\Scripts\python.exe dashboards/powerbi/prepare_desktop.py
```

Open `artifacts/powerbi/project/RetailPulse.pbip` in Power BI Desktop and refresh.
The pages are **Executive Overview**, **Store & Product Diagnostics** and
**Forecast Performance**. The import uses 11,646 daily summaries, 512,076
product-week summaries and 412,608 historical forecast observations. Gold
remains the canonical metric source. WMAPE uses a ratio of totals, partial
revenue is labeled, and the model's RMSE regression remains visible.

Follow the [build guide](dashboards/powerbi/BUILD_GUIDE.md),
[dashboard specification](dashboards/powerbi/dashboard_spec.md) and
[DAX measure contract](dashboards/powerbi/measures.md). The local
`dashboards/powerbi/RetailPulse.pbix` contains real data and is not distributed.
No Power BI sign-in or cloud publication is required.

## Local grounded assistant

Use the existing Gold snapshot without rerunning the pipeline or models:

```powershell
.\.venv\Scripts\python.exe -m retailpulse ask "How many units did CA_1 sell during April 2016?"
.\.venv\Scripts\python.exe -m retailpulse ask "Compare LightGBM and rolling mean WMAPE on the test period"
.\.venv\Scripts\python.exe -m retailpulse ask "What does revenue_proxy mean?"
.\.venv\Scripts\python.exe -m retailpulse agent-eval
```

The approved tools are `get_kpi`, `get_forecast` and `search_metric_docs`.
Every numerical answer includes its filters, period and Gold provenance.
The first example returns **25,307 units** for April 2016 in `CA_1`.
Questions about current sales, inventory or causation receive explicit
limitations. English routing supports documented question patterns and asks
for clarification when scope is ambiguous.

`--provider deterministic` disables the Ollama probe. By default the assistant
checks the local endpoint and falls back explicitly if no installed model can
be used. It never downloads models. `ask --json` exposes the typed result.
Explicit `--provider ollama --ollama-model qwen2.5:1.5b` requires a live
selection for routed requests; fallback returns a nonzero exit code. Safe
provider diagnostics distinguish connectivity, timeout, generation and
validation failures. Cold loading uses a bounded 30-second chat timeout.
Runtime traces and evaluation outputs stay under ignored `artifacts/agent/`.
See the [demo and activation guide](docs/agent_demo.md),
[safety contract](docs/agent_safety.md) and [RP-09 evidence](docs/evidence/rp09_gate.md).
The reusable core is ready for a future API adapter; RP-10 has not started.

See the [product brief](docs/product_brief.md), [scope](docs/scope.md) and
[target architecture](docs/architecture.md).
