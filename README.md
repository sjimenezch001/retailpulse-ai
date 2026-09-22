# RetailPulse AI

Retail demand analytics platform. It aims to turn historical sales,
calendar data and prices into verifiable business metrics for comparing
stores and departments, reducing fragmented analysis and inconsistent
business definitions.

**Status: RP-01 — Repository, environment and standards.** Python foundation
with packaging, local configuration, an import test and linting. The M5 dataset
is not yet included or downloaded; ingestion is not implemented.

Initial stack: Python 3.12, pandas, PyArrow, DuckDB, Pydantic and PyYAML.
Development: pytest and Ruff. Packaging: setuptools and pip.

## Repository structure

```text
config/local.yaml      Relative paths and pending pilot selection
data/sample/           Small samples suitable for version control
data/contracts/        Data contracts
notebooks/             Exploration
sql/{silver,gold,checks}/
src/retailpulse/        Python package (version 0.1.0)
  ingestion/ transforms/ quality/ features/ models/ api/ agent/
tests/                 Smoke test; unit/ and integration/ reserved
docs/                  Product, scope, architecture and evidence/
pyproject.toml         Metadata, dependencies and tool configuration
requirements.txt       Exact versions from the validated environment
.env.example           Template without credentials
```

The reserved subpackages and directories do not yet contain functionality.
Raw and processed data and generated artifacts are excluded from Git.

## Quick Start — Windows PowerShell

From the repository root, use Python 3.12 (validated with 3.12.10).
Only if `.venv` does not already exist, create it with `py -3.12 -m venv .venv`.
The following commands use that environment directly, without activation:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

`pyproject.toml` is the primary source of configuration. `requirements.txt`
pins the direct and transitive dependencies validated on Windows with Python
3.12; installing it first reproduces those versions. The local package
is then installed in editable mode. pytest uses the package installed from
`src/` and discovers tests in `tests/`.

`config/local.yaml` reserves the paths `data/raw` and `data/processed`, relative
to the repository root. Stores and departments remain unselected.
No secrets or `.env` file are required at this stage.

See the [product brief](docs/product_brief.md), [scope](docs/scope.md) and
[target architecture](docs/architecture.md).
