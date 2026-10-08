# RP-10 gate — Local FastAPI and Streamlit demo

**RP-10 ENGINEERING: PASS**

**RP-10 FULL GATE: PASS**

Validated on 2026-10-08 UTC, Windows, Python 3.12.10, Chrome 154.0.8037.98.
Branch: `feat/rp-10-web-demo`, based on verified remote main
`774035e82ad183d1fc13dd21cb90c5af73348fb5`. This is local acceptance;
no push, merge, PR, public deployment, RP-11 or RP-13 work was performed.
The implementation and portable tests are committed locally as `efadf27`
(`feat: add local FastAPI and Streamlit portfolio demo`). Documentation and
the acceptance artifacts are recorded in the following local evidence commit.

## Implemented and exercised

| Check | Actual result |
|---|---|
| `/health` | HTTP 200, real and synthetic dataset metadata; model availability and explicit degraded state contract |
| `/metrics/summary` | HTTP 200; real totals and April CA_1 scope reconcile with independent read-only SQL |
| `/forecast` | HTTP 200; both historical test models reconcile with RP-08's recorded evaluations |
| `/assistant/query` | HTTP 200; genuine Ollama and explicit deterministic responses both return grounded 25,307 units |
| Invalid input | HTTP 422 for attempted SQL field; portable tests also exercise type/date/model validation, forbidden fields, host/origin, body/query bounds and timeout errors |
| Overview | Rendered in Chrome; exact 3,790-day freshness, price coverage, revenue caveat, trend and comparisons |
| Forecast | Rendered in Chrome; two distinct predictions versus actuals; WMAPE/MAE/RMSE and the RMSE tradeoff visible |
| Ask RetailPulse | Genuine browser click produced a successful Ollama answer; portable browser used deterministic routing |
| Architecture | Rendered in Chrome; actual pipeline, documentation links and limitations |
| Store interaction | Real: 4,530,250 → 1,477,827 units for CA_1. Synthetic: 1,386 → 378 for SYN_A |
| Browser errors | Zero page errors and zero Streamlit exception elements in both acceptance runs |
| Startup / shutdown | Both commands reported readiness. Ctrl+C terminated all 12 owned Python launcher/server processes, including Windows executable wrappers; ports 8000/8501/8001/8502 were closed afterward |
| Preservation | Real Gold and all 45 frozen RP-07 artifacts retain their prior SHA-256 hashes |

The launcher was tested with:

```powershell
.\.venv\Scripts\python.exe -m retailpulse demo
.\.venv\Scripts\python.exe -m retailpulse demo --mode synthetic --provider deterministic --api-port 8001 --ui-port 8502
```

Default URLs: UI <http://127.0.0.1:8501>, API <http://127.0.0.1:8000>,
OpenAPI <http://127.0.0.1:8000/docs>. All test servers were stopped afterward.
The terminal wrapper reported an interrupted exit on Ctrl+C; the launchers
printed their cleanup messages and process/port checks confirmed complete cleanup.

## Real findings and provider evidence

Gold run `20f4dae75fff8e79204e` covers 2011-01-29–2016-05-22, with snapshot
as-of 2026-10-07. The API preserves 4,530,250 units, 72.6631056% price coverage,
13,500,903.56 known-price revenue proxy, 977,382 missing-price observations and
380,925 demand spike flags. Complete `revenue_proxy` remains unknown. Freshness
is exactly 3,790 days at the stored as-of date, not a live commercial indicator.

| Historical test model | WMAPE | MAE | RMSE |
|---|---:|---:|---:|
| `lightgbm_global_v1` | 0.748259584 | 1.268324367 | 2.431176620 |
| `rolling_mean` | 0.794823526 | 1.347251767 | 2.361193998 |

The final recorded API acceptance returned `ollama:qwen2.5:1.5b`, diagnostic
`status=succeeded`, `stage=complete`, zero validation errors, and
`live_provider_succeeded=true`. It answered the April CA_1 question with
25,307 units in **8.947 seconds** end-to-end. Deterministic routing answered
the same question in **0.205 seconds** with `live_provider_succeeded=false`.
The initial cold API smoke call took 25.531 seconds; the genuine browser
Ollama answer displayed 9.91 seconds. These are individual local observations,
not a throughput benchmark. No fallback was counted as a live-model success.
RP-09's prior 36-question evaluation remains intact; RP-10 adds application
acceptance rather than claiming a new 36-question model evaluation.

The recorded real API requests took 0.130 seconds for health, 0.193 for a cached
summary, 0.867 for the April scope, and 0.115 for the cached forecast. Initial
uncached summary/forecast smoke calls took 2.000/0.245 seconds. Cache state and
model warming affect these measurements.

Public machine-readable evidence:

- [Real API reconciliation and safe provider diagnostic](rp10/real_api.json)
- [Real browser acceptance](rp10/real_browser.json)
- [Synthetic browser acceptance](rp10/synthetic_browser.json)
- [Process cleanup and integrity checks](rp10/lifecycle.json)

Local full smoke responses are in ignored `artifacts/rp10/real_api.json`.
Sanitized per-question traces and process logs are in ignored
`artifacts/web_demo/real/` and `artifacts/web_demo/synthetic/`.
Public evidence contains aggregate values and safe metadata only.

## Portable mode and safeguards

Six packaged CSVs derive only from repository-authored synthetic fixtures.
They contain 252 daily observations and six series totaling 1,386 units;
the illustrative ML comparison is simulated and labeled accordingly. Rebuilding
the snapshots twice produced byte-identical CSVs. Runtime startup only loads
them into an ignored database. It never downloads M5, trains a model or touches
real Gold. Synthetic retrieval uses a separate small glossary without real
M5 results. Missing real Gold cannot trigger silent substitution.

Genuine startup exposed a Windows ACL issue when a temporary database was
renamed out of a private temporary directory. Publication now copies into a
sibling staging file before atomic replacement, inheriting the serving
directory's permissions. Portable startup and browser acceptance passed after
this fix. No user raw files or real databases were removed or modified.

Strict tool allowlists, validated arguments, deterministic numerical answers,
grounding and read-only database protections remain in the RP-09 core.
The API adds closed schemas, bounded requests/concurrency and sanitized errors.
Tests cover version-aware cache reuse/invalidation, source isolation, missing
prices, unavailable Ollama and explicit UI fallback disclosure. No provider
response text, credentials, SQL or private paths are included in diagnostics.

## Regression and environment

`python scripts/verify.py`, using `.venv\Scripts\python.exe`, exited successfully:

- **pytest:** 200 passed in 93.34 seconds; original 163 plus 37 new tests.
- **Ruff:** all checks passed.
- **pip check:** no broken requirements.
- **git diff --check:** passed.

The suite reported three non-failing warnings: Starlette's HTTPX test-client
deprecation, the existing MLflow/SQLAlchemy loader deprecation, and a sandbox
permission warning for pytest's optional cache. No test failures were hidden
or skipped. Existing tests were not modified.

All 62 earlier exact dependency pins are preserved; all 83 resulting pinned
packages match the installed environment. FastAPI 0.142.4 and Uvicorn 0.54.0
are now explicit runtime dependencies alongside Streamlit 1.65.0, HTTPX 0.28.1
and Altair 6.3.0. Editable installation succeeded with the declared isolated
build backend. Tests use synthetic sources and mocked discovery; browser and
real-data checks are separate opt-in scripts. The existing Linux CI workflow
can run the portable suite, but remote CI was not executed because nothing
was pushed.

## Genuine screenshots

Captured with headless installed Chrome and Playwright against the running
local application; these are real renders, not mockups.

| Tab / interaction | Real mode | Synthetic mode |
|---|---|---|
| Overview | [Screenshot](rp10/real_overview.png) | [Screenshot](rp10/synthetic_overview.png) |
| Store filter | [Screenshot](rp10/real_filtered.png) | [Screenshot](rp10/synthetic_filtered.png) |
| Forecast | [Screenshot](rp10/real_forecast.png) | [Screenshot](rp10/synthetic_forecast.png) |
| Assistant | [Screenshot](rp10/real_assistant.png) | [Screenshot](rp10/synthetic_assistant.png) |
| Architecture | [Screenshot](rp10/real_architecture.png) | [Screenshot](rp10/synthetic_architecture.png) |

No remaining gate blockers. This remains a local portfolio demo: historical
M5, no operational inventory data, no authentication or production hosting,
no future LightGBM output. See the [launch guide and 150-second script](../web_demo.md)
and [API examples](../api_examples.md).
