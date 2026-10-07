# Early CI guardrails — 2026-10-07

A minimal GitHub Actions workflow installs Python 3.12, the existing pinned
requirements and the editable project, then runs pip check, Ruff and pytest.
It uses repository synthetic fixtures only, read-only repository permissions,
and no dataset downloads or project secrets. It does not complete RP-11.
Workflow usage follows the official [checkout](https://github.com/actions/checkout)
and [setup-python](https://github.com/actions/setup-python) documentation.

`scripts/verify.py` runs the same local checks plus `git diff --check` using the
invoking environment. README and architecture now state the implemented stages
and real-data limitation. The profiling notebook includes valid cell IDs.

The CLI integration test executes profile → Bronze → Silver → Gold → baselines
and business queries inside a temporary synthetic project. It also checks
reruns and nonzero failures for missing source files, without modifying real
configuration, manifest or sample directories.

Validation:

- `python -m pytest -p no:cacheprovider`: `53 passed in 44.98s`.
- Final `python -m pytest`: `53 passed, 1 warning in 46.61s`.
- Warning: the pre-existing local `.pytest_cache/v/cache` directory denies write
  access. Tests pass; the cache-disabled run is warning-free. No ACLs or global
  configuration were changed.
- `python -m ruff check .`: `All checks passed!`.
- `python -m pip check`: `No broken requirements found.`
- `git diff --check`: exit 0; no whitespace errors.
- Workflow YAML parsed successfully; Python version, triggers and permissions checked.

The hosted workflow has NOT run: this branch has not been pushed. Linux runtime
validation and a GitHub Actions run remain pending. Dependency files are unchanged.

## Subsequent validation context

At the start of real M5 validation, the user confirmed that the early workflow
had passed remotely. No remote workflow was triggered or GitHub state changed
during this validation task; the statement above records the original local
sprint state. Current local regression results are in the sprint report.
