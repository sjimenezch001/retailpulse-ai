# RetailPulse AI

Retail demand analytics platform. It turns historical sales, calendar data and
prices into verifiable business metrics for comparing stores and departments,
reducing fragmented analysis and inconsistent business definitions.

**Status: RP-02–RP-06 REAL-DATA VALIDATED** on the configured M5 pilot. RP-00
and RP-01 are complete. Real profiling, Bronze/Silver/Gold, baseline evaluation
and exact rerun checks passed. Full inputs and generated datasets remain local
and Git-ignored; the report records measurements and remaining limitations.

Stack: Python 3.12, pandas, PyArrow, DuckDB, Pydantic and PyYAML.
Development: pytest and Ruff. Packaging: setuptools and pip.

## Repository structure

```text
config/local.yaml      Relative paths and the derived real M5 pilot
data/contracts/        Inspected source manifest with hashes and profiles
data/sample/           Local-only M5 samples; tracked guidance and provenance
notebooks/             Thin profiling notebook
sql/{silver,gold,checks,queries}/
src/retailpulse/        data/, ingestion/, transforms/, quality/, models/
                       features/, api/, agent/ reserved for later stages
tests/                 Synthetic fixtures, unit, integration and SQL checks
docs/                  Source, metrics, dictionary, baselines and gate evidence
scripts/verify.py      Local checks using the invoking Python environment
.github/workflows/     Early CI; no datasets or secrets required
pyproject.toml         Metadata, dependencies and tool configuration
requirements.txt       Exact versions from the validated environment
.env.example           Template without credentials
```

Raw and processed data, real M5 samples and generated artifacts are excluded from Git.
Real row-level samples are generated locally and are not distributed in the repository.
The synthetic fixtures are stored only under `tests/fixtures/`.

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

Read the [metric catalog](docs/metric_catalog.md), [data dictionary](docs/data_dictionary.md),
[baseline protocol](docs/baselines.md) and [sprint report](docs/evidence/DATA_BACKBONE_SPRINT_REPORT.md).
`revenue_proxy` is a proxy, not audited revenue; M5 provides no real inventory.
Early CI is a guardrail, not completion of RP-11. RP-07 has not started.

See the [product brief](docs/product_brief.md), [scope](docs/scope.md) and
[target architecture](docs/architecture.md).
