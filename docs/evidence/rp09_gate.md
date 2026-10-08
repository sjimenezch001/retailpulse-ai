# RP-09 — Grounded assistant gate

**RP-09 ENGINEERING: PASS**

**RP-09 FULL GATE: PENDING LIVE LLM VALIDATION**

Validated locally on 2026-10-07 with Python 3.12.10. Work started from clean,
synchronized `main` at `476310e93d398e2be3ca213e4fdfaae437afdc41` on
`feat/rp-09-agent`. The implementation adds no dependencies, retraining,
pipeline changes, HTTP endpoints or cloud deployment. RP-10 has not started.

## Engineering acceptance

| Requirement | Evidence |
| --- | --- |
| Three approved tools | `get_kpi`, `get_forecast`, `search_metric_docs`; typed requests/results |
| Read-only query boundary | Fixed aggregate templates, bound values, identifier/enumeration checks, DuckDB read-only plus locked external-access restrictions |
| Bounded work | 100 output rows; session SQL deadline; 256 MB DuckDB budget; one thread; no temporary spill |
| Grounded answers | Deterministic renderer; provider cannot supply figures or change validated scope |
| Traceability | Period, filters, units, source table, run ID, freshness and generation time; ignored metadata-only traces |
| Document grounding | Five approved local documents, lexical retrieval, real line references, no executable document instructions |
| Portable regression suite | 74 RP-09 tests plus all 75 existing RP-00–RP-08 tests pass |
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
Median measured case latency was **19.397 ms**, maximum **318.059 ms**;
these measurements include independent reconciliation but exclude initial
provider discovery. All cases used the explicitly labeled deterministic
fallback. See [machine-readable evaluation](rp09_evaluation.json).

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

## Ollama

- Installed: **NO**, based on PATH and standard local installation checks.
- Loopback model endpoint reachable: **NO**.
- Model validated: **NO**; model name: not applicable.
- Model downloads performed: **none**.
- Adapter validation: strict-schema and transport mocks only.

The optional adapter uses loopback HTTP with timeouts, no proxy/redirects,
bounded responses and exact scope validation. Supported responses remain
available through deterministic fallback. No live model result is claimed.

The remaining full-gate step is to install/start Ollama and validate an
available model. Downloading a model first requires explicit authorization.
Run the commands in the [activation guide](../agent_demo.md#ollama-status-and-activation),
verify actual `ollama:<model>` selections rather than fallback, and record
the model, grounded outcomes and latency. This is the only full-gate blocker.

## Validation

| Check | Result |
| --- | --- |
| `python -m pytest -p no:cacheprovider` | 149 passed in 59.12 seconds |
| `python -m ruff check .` | All checks passed |
| `python -m pip check` | No broken requirements found |
| `python scripts/verify.py` | PASS; 149 tests passed in its test phase |
| `git diff --check` | PASS |
| Synthetic golden evaluation | 36/36 |
| Real `python -m retailpulse agent-eval` | 36/36, explicit deterministic fallback |

The full suite emitted an existing MLflow/SQLAlchemy deprecation warning.
The verify script also emitted a non-failing pytest cache permission warning
in this Windows environment. Neither changed dependencies or test outcomes.
Runtime outputs remain under ignored `artifacts/agent/`; the public trace
sample is explicitly illustrative and redacted.

Work is committed locally on `feat/rp-09-agent`. No push, merge, PR or RP-10
work was performed. Use `git log main..HEAD --oneline` for the local commits.
