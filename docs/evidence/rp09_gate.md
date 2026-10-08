# RP-09 — Grounded assistant gate

**RP-09 ENGINEERING: PASS**

**RP-09 FULL GATE: PASS — LIVE OLLAMA VALIDATED**

Validated locally on 2026-10-07 with Python 3.12.10. Work started from clean,
synchronized `main` at `476310e93d398e2be3ca213e4fdfaae437afdc41` on
`feat/rp-09-agent`. The implementation adds no dependencies, retraining,
pipeline changes, HTTP endpoints or cloud deployment. RP-10 has not started.
The live follow-up was recorded on 2026-10-08 UTC (2026-10-07 local), starting
from clean RP-09 commit `b8958d0`, using the already installed Ollama model.

## Engineering acceptance

| Requirement | Evidence |
| --- | --- |
| Three approved tools | `get_kpi`, `get_forecast`, `search_metric_docs`; typed requests/results |
| Read-only query boundary | Fixed aggregate templates, bound values, identifier/enumeration checks, DuckDB read-only plus locked external-access restrictions |
| Bounded work | 100 output rows; session SQL deadline; 256 MB DuckDB budget; one thread; no temporary spill |
| Grounded answers | Deterministic renderer; provider cannot supply figures or change validated scope |
| Traceability | Period, filters, units, source table, run ID, freshness and generation time; ignored metadata-only traces |
| Document grounding | Five approved local documents, lexical retrieval, real line references, no executable document instructions |
| Portable regression suite | 88 RP-09 tests plus all 75 existing RP-00–RP-08 tests pass |
| Real-data acceptance | 36 golden outcomes plus six numerical demonstration questions reconcile independently |
| Reusable orchestration | `Assistant.ask` and Pydantic contracts have no CLI/HTTP dependency |

## Golden questions

The same [versioned questions](../../tests/agent/golden_questions.yaml) run on
a generated synthetic Gold fixture and separately on the local real M5
snapshot. Expected arguments come from YAML, not from the router's output.

| Category | Total | Passing |
| --- | ---: | ---: |
| Numerical, including forecasts | 16 | 16 |
| Definitions | 4 | 4 |
| Ambiguous / unsupported | 10 | 10 |
| Adversarial | 6 | 6 |
| Total | 36 | 36 |

Real M5 evaluation produced **20 answers** and **16 correct safe refusals or
clarifications**. Numerical grounding accuracy and provenance coverage were
both **100%** across the 16 numerical cases. Missing canonical revenue was
correctly reported as unknown rather than replaced by its partial sum.
The strict live run used **22 genuine validated `ollama:qwen2.5:1.5b` calls**
and **14 preflight outcomes**, with **zero fallback cases**. Twenty calls
returned grounded answers; two correctly reached tool-level refusals.
Preflight cases do not count as model calls. All 22 required selections
passed, and all 36 expected outcomes passed.

| Measured latency | Median | Maximum |
| --- | ---: | ---: |
| All 36 cases, including tool execution and independent reconciliation | 3,707.073 ms | 12,291.498 ms |
| 22 successful model selections only | 8,398.5 ms | 12,156 ms |

Provider discovery is excluded. The model was loaded for this full-suite run;
a separate controlled cold request took **14,594 ms**, including **7,115.4255
ms** loading. These are local measurements, not performance guarantees.
See [final live evaluation](rp09_live_evaluation.json). The
[original deterministic evaluation](rp09_evaluation.json) is retained as
historical engineering evidence; it is not counted as live validation.

The evaluator independently queries Gold, checks forecast metrics against
`forecast_evaluation`, validates periods/scopes and verifies excerpt text
against cited lines. An initial real-only date comparison failure exposed
the distinction between Gold TIMESTAMP and fixture DATE values. The reference
query now compares calendar dates explicitly, and the synthetic fixture uses
the real timestamp type. No tolerance or safety restriction was weakened.

## Real M5 acceptance and unchanged artifacts

Gold run: `20f4dae75fff8e79204e`. Observations end on **2016-05-22**;
`as_of_date` is **2026-10-07**, giving **3,790 days** of historical freshness.

Independent checks confirmed **4,530,250 total units**, **25,307 CA_1 units in
April 2016**, and store/department changes over consecutive 28-day periods.
LightGBM test WMAPE remains **74.825958%**, versus **79.482353%** for rolling
mean. LightGBM's worse RMSE remains visible: **2.431177 vs 2.361194**.
The [six numerical acceptance examples](rp09_real_acceptance.json) retain full
aggregate precision, filters and provenance. No row-level observations are
included in public evidence.

Gold SHA-256 remains
`7228489a792fcf4e464014f729313c8731180621df378e31567894cccba7e620`.
It matches [RP-08's audit](rp08_data_audit.json); all **45 frozen RP-07
artifact hashes** also match. Existing training, evaluation and BI results
were preserved. Raw M5 files and generated datasets remain local and ignored.

## Security and truthful limitations

Tests cover SQL injection, arbitrary table/tool selection, forbidden writes
and ATTACH, external file reads, configuration changes, secret requests,
question/document prompt injection, unknown metrics/filters, inconsistent
lineage, invalid/future dates, row limits and an actively interrupted query.
They also verify missing-price semantics, all-missing prices, weighted error
metrics, zero-denominator WMAPE, deterministic answers, redacted traces,
provider timeout/unavailability, unsupported provider figures and changed
filter proposals. Extra unsupported conditions request clarification.

The assistant explains that historical observations are not current sales;
M5 has no actual inventory; zeros do not prove stockouts; revenue is a proxy;
spikes do not prove causation; and LightGBM has no operational future output.
English parsing is deliberately bounded and stateless. Spanish, arbitrary
rankings and conversational follow-ups are not implemented. Resource and
host-trust limits are described in the [safety contract](../agent_safety.md).

## Ollama diagnosis and live acceptance

- Installed and API reachable: **YES**, version **0.40.0**.
- Model validated: **YES**, **qwen2.5:1.5b**, Q4_K_M, 986,061,892 bytes.
- Model digest: `65ec06548149b04c096a120e4a6da9d4017ea809c91734ea5631e89f96ddc57b`.
- Model downloads performed: **none**.
- Full-gate blockers: **none** on this validated local configuration.

The host initially refused loopback connections because the service was not
running. Starting the installed service resolved discovery. The original
adapter then timed out at **10,052.182 ms**. The measured cold request exceeds
that budget, so the default was raised to its existing 30-second maximum.
HTTP/API compatibility was verified; the example's generated JSON, strict
schema and exact argument scope all validated successfully.

The first full live run additionally exposed two scope mismatches and one
schema rejection. It scored **33/36**, with **19 genuine model calls**,
**three fallbacks** and **14 preflight outcomes**; see the
[preserved failed run](rp09_live_initial_evaluation.json). A clearer selection
prompt preserves null filters and copies documentation queries verbatim.
After targeted retests, a complete unchanged-suite rerun passed **36/36**
with **22/22** required model selections and **zero fallbacks**.

The user's exact CLI example subsequently reported `ollama:qwen2.5:1.5b`
and **25,307 units**, with a successful provider diagnostic (11,109 ms).
The full schema, allowlists, validation, exact scope equality, numerical
grounding and read-only Gold protections were not relaxed. Diagnostic metadata
contains no raw questions, generated text, credentials or provider error bodies.
Explicit Ollama CLI/evaluation mode returns nonzero on fallback; automatic mode
retains its labeled functional fallback. The model confirms application scope;
it does not independently calculate figures or provide unrestricted reasoning.
See [diagnosis and repair](rp09_live_ollama.md),
[safe diagnostic evidence](rp09_live_diagnostics.json) and the
[activation guide](../agent_demo.md#ollama-status-and-activation).

## Validation

| Check | Result |
| --- | --- |
| `python -m pytest -p no:cacheprovider` | 163 passed in 88.97 seconds |
| `python -m ruff check .` | All checks passed |
| `python -m pip check` | No broken requirements found |
| `python scripts/verify.py` | PASS; 163 tests passed in its test phase (83.00 seconds) |
| `git diff --check` | PASS |
| Synthetic golden evaluation | 36/36 |
| Real `python -m retailpulse agent-eval --provider ollama --ollama-model qwen2.5:1.5b` | 36/36; 22 validated model calls, 14 preflight outcomes, zero fallback |

The full suite emitted an existing MLflow/SQLAlchemy deprecation warning.
The verify script also emitted a non-failing pytest cache permission warning
in this Windows environment. Neither changed dependencies or test outcomes.
Runtime outputs remain under ignored `artifacts/agent/`; the public trace
sample is explicitly illustrative and redacted.

Work is committed locally on `feat/rp-09-agent`. No push, merge, PR or RP-10
work was performed. Use `git log main..HEAD --oneline` for the local commits.
