# RP-02 gate — 2026-10-07

Status: CODE COMPLETE; REAL-DATA VALIDATION PENDING.

Source, schema, acquisition instructions, inventory limitations, deterministic
pilot selection and real-sample provenance are documented. The three required
M5 files were not detected. No real checksums or sample are claimed. The checked-in
manifest is pending and the configured pilot remains empty.

Validation using only labeled synthetic fixtures:

- `python -m pytest -p no:cacheprovider`: `9 passed in 0.86s`.
- `python -m ruff check .`: `All checks passed!`.
- `git diff --check`: exit 0; Git reports local CRLF normalization information.
- Source checksums repeat for unchanged test files; missing inputs and duplicate
  price keys are rejected; schema and coverage reports are tested.

The pre-existing pytest cache has a Windows access restriction. Stage checks
disable the optional cache provider without changing test execution. Python
3.12.10 and the existing environment are reused; dependencies are unchanged.

Pending: obtain real M5 files, inspect them, derive the pilot, review source
quality and produce a real sample before claiming the real-data gate passes.
