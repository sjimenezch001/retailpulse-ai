# Reproducible developer workflow

Use Python 3.12. From PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python scripts/tasks.py setup
```

On Linux/macOS, use `python3.12 -m venv .venv` followed by
`source .venv/bin/activate`, then the same task commands. They always use the
invoking Python and propagate failures. No shell-specific task runner is required.

| Task | Command |
| --- | --- |
| Install validated application/tool pins | `python scripts/tasks.py setup` |
| Ruff | `python scripts/tasks.py lint` |
| Scoped strict mypy | `python scripts/tasks.py typecheck` |
| Portable tests and coverage | `python scripts/tasks.py test` |
| Dependency and full-tree secret scans | `python scripts/tasks.py security` |
| Offline secret scan only | `python scripts/tasks.py secrets` |
| Wheel and sdist | `python scripts/tasks.py build` |
| Portable synthetic demo | `python scripts/tasks.py demo` |
| Local lint/types/tests/pip/diff | `python scripts/tasks.py verify` |
| Container build, when Docker is installed | `python scripts/tasks.py docker` |

`python scripts/verify.py` remains supported and delegates to `verify`. Security
scanning is separate because the dependency advisory lookup requires internet;
GitHub Actions runs both and fails on either error. Reports go to ignored `reports/`.
Tests use synthetic fixtures, including tiny synthetic model training for existing
model regression tests; no real model retraining or network model download occurs.

`requirements.txt` preserves all RP-10 application pins. `requirements-dev.txt`
adds exact tool and transitive versions and remediates pip. The container installs
the 74 pinned runtime dependencies in `requirements-runtime.txt`, excluding
pytest, Ruff and browser automation. Review all lock changes together; runtime
pins are a subset of the validated application lock. Python wheels remain
platform-specific; CI checks installation on Windows and Linux.

Type checking is strict for agent/HTTP contracts, Spanish normalization and safe
event construction. Imported legacy modules are followed silently, not claimed
as checked. There are no blanket missing-import ignores or disabled error codes.
Coverage includes all `src/retailpulse` and `app` code, with branches, and enforces
85%. Reports include the actual uncovered lines. CLI subprocesses and opt-in
browser execution are not included in this in-process coverage percentage.

Optional local hooks use this activated environment:

```powershell
python -m pre_commit install
python -m pre_commit run --all-files
```

## Portable container

Docker Engine/Desktop and Compose v2 are prerequisites. This definition packages
only code, synthetic CSVs and the demo guide. It does not package real M5, Gold,
frozen models, PBIX, Git history, host caches or secrets.

```powershell
docker compose -p retailpulse-demo config --quiet
docker compose -p retailpulse-demo build
docker compose -p retailpulse-demo up -d --wait --wait-timeout 120
python scripts/check_portable.py
docker compose -p retailpulse-demo down
```

Open `http://127.0.0.1:8501`; API readiness is `http://127.0.0.1:8000/ready`.
Stop the existing local demo first if it owns these ports. The image binds inside
its network namespace; Compose publishes only to localhost. Never replace those
host bindings with public interfaces. No authentication or public hosting is added.

The image uses a digest-pinned Python 3.12 base, UID 10001, no Linux capabilities,
no privilege escalation and a read-only Compose root filesystem. Synthetic runtime
files live in a disposable tmpfs. No mounts expose host datasets. Shutdown removes
only the named project's containers; never use global prune commands. Real mode
is rejected by the container launcher. Ollama remains optional and is not included.

Docker was not installed during local RP-11 acceptance. Static inspection is not
a build or startup test. The existing CI workflow has an actual image build,
health wait, API/UI smoke test, non-root check and unconditional project cleanup;
those results remain pending until an authorized remote run.
