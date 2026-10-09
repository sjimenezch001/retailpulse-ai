# RP-12A gate — AWS showcase implementation and offline validation

Date: 2026-10-08. Branch: feat/rp-12-aws-showcase.
Baseline: synchronized, clean main at the owner-specified caa6389 revision.
The full baseline revision was verified against local main, origin/main and the
fetched remote before creating this branch.

## Status

Implementation: **PASS (offline scope)**. AWS resources created: **NONE**.
AWS live acceptance: **NOT RUN**. Native Spark/Glue: **NOT RUN**, because
Java and PySpark are unavailable on this workstation.
Redshift: **DISABLED / ACCESS UNVERIFIED**.

The [runbook](../aws_runbook.md), [cost controls](../aws_cost_controls.md) and
[Redshift extension note](../aws_redshift_extension.md) document the implementation
and prerequisites. No account/profile was inspected, STS called, real account
plan generated, resource provisioned, data uploaded or workload executed.
Only prepare and validate were executed through the lab runner.

## Implemented scope

- Explicit synthetic manifest/CSV allowlist, aggregate input limit and schema,
  key, null, date, provenance and nonnegative-value checks.
- Genuine Glue-compatible PySpark batch code, deterministic run identity,
  partial-run overwrite and completed-run logical readback reconciliation.
- Five explicit Parquet catalog tables, six allowlisted analytical queries and
  publication only after actual future Athena reconciliation.
- Private SSE-S3/TLS storage, execution-role separation, bounded workgroup/job,
  short retention, optional AWS_IAM HTTP API and artifact-backed Lambda.
- Exact account/profile/region/environment controls, explicit future mutation
  confirmation and ownership-verified teardown with preserved recovery state.
- Isolated pinned SDK, pinned/checksummed Terraform and provider lock,
  network-blocked Python tests and an offline-only CI extension.
- Local application source, runtime dependency pins and package version unchanged.

The independent references derive **1,386 units**, **252 facts**, stores SYN_A
378 / SYN_B 462 / SYN_C 546, three stores, two products and six store/item series.
Date bounds are 2020-01-01 through 2020-02-11. Approved input size is **55,218
bytes**, below 10 MiB. Synthetic forecasts are excluded from uploads.
PyArrow round trips test local serialization; stubbed Glue publication tests
are not native Spark or AWS execution.

## Validation record

| Check | Actual result |
| --- | --- |
| Terraform 1.15.9 fmt/init/validate | PASS; backend disabled, lock file read-only, AWS provider 6.68.0. |
| Terraform explicitly mocked plans | 4 passed, 0 failed; no apply or AWS provider account calls. |
| New offline data/SQL/endpoint/security tests | 89 passed in 27.66 seconds; real sockets blocked. |
| Local synthetic preparation | PASS; Python/DuckDB reconciliation and PyArrow Parquet round trips. |
| Existing full verification | PASS: 343 tests (254 original + 89 new), 2 warnings, 447.82 seconds; 88.15% statement/branch coverage, threshold 85%. |
| Existing dependency audit | PASS; 123 pinned packages, zero skipped entries and no known vulnerabilities. |
| Isolated AWS SDK audit | PASS; all 7 pinned packages, zero skipped entries and no known vulnerabilities. |
| Secret scanner | PASS with all detectors and the existing exact baseline; no new exceptions required. Final documentation is included in the closing scan. |
| Wheel and source build | PASS; version 0.1.0, no cloud SDK/infra/state/media included. |
| Internal links | PASS: 234 checked, zero errors. |
| Protected assets | All 52 before/after SHA-256 values match, including Gold and all 45 frozen artifacts; the frozen file set also matches. |
| Linux/Windows required CI and container | Existing job definitions/steps unchanged; remote CI and Docker were not executed in this stage. |

Public source provenance: Terraform archive checked against HashiCorp's published
SHA-256; all 16 provider archive hashes match the official 6.68.0 checksum list;
the installed Windows provider content hash matches the committed lock. The
lock also includes Linux AMD64 from the signed provider-lock operation. The
seven SDK packages came from the official Python package index with archive
hashes. SDK installation stayed under ignored artifacts/rp12/sdk/.

Ignored local receipts: artifacts/rp12/prepare_result.json, validate_result.json,
verify.log, preservation_before.json, preservation_after.json,
preservation_and_packaging.json and internal_links.json; reports/coverage.json,
dependencies.json, aws_dependencies.json and secrets.json. These are actual
local evidence, not cloud execution receipts. No credential values are recorded.

Ruff passed; mypy passed its existing four-file strict scope; pip check reported
no broken requirements; git diff --check passed. The two pytest warnings are
existing Starlette/httpx and MLflow/SQLAlchemy deprecations, without failures.
A [machine-readable summary](rp12/offline.json) records the actual counts.

The configured application coverage gate remains >=85%, covering
src/retailpulse and app with branch coverage. Cloud tests extend the suite but
are not included in that line-coverage percentage. Existing Windows/Linux/
container CI names and steps are preserved; no GitHub Actions run was triggered.

## Corrective evidence and limitations

The closing scanner correctly failed on a secret-keyword false positive in the
new JSON summary: a prose status string under secret_scan. It is now represented
as a structured status object. No credential was present, no detector/filter
was changed and no baseline exception was added. Windows documentation writes
were also corrected to use explicit UTF-8 before the closing link/diff checks.

The first mocked infrastructure check rejected a 10,000,000-byte Athena cutoff.
The pinned provider requires at least 10,485,760 bytes; the configuration and
assertions now use that value. An offline test-guard regular expression also
rejected valid plan commands; the guard now checks extracted command tokens and
has negative tests for apply, real providers and alternate modules.

Glue trust retains SourceAccount and SourceArn conditions. Their real service
context propagation remains unverified; do not silently remove them if role
assumption fails. Automatic approval review rejected a proposed removal as a
security weakening; no such removal was applied. The remaining authorized
offline implementation continued with the restrictions intact.

No measured Glue/Athena runtime, cloud costs, service eligibility, live IAM
authorization or real endpoint response is claimed. HTTP client tests use fake
transport/signing; actual unsigned 403 and signed 200 acceptance remains pending.
Mock plans establish configuration assertions only, not live deployability.
Future partial-deployment cleanup can require owner-reviewed recovery if exact
ownership cannot be established.

The modelled regional experiment is approximately **USD 0.41 gross**, rounded
up to a $0.50 baseline with a $1.50 planning reserve, inside the $5 target.
No credits are deducted and no dollar hard cap or spending authorization is
implied. See the official sources and assumptions in the cost document.

The historical RP-13 approvals remain intact. Independent human quick-start
verification is **PENDING, deferred by the owner**. Public video hosting,
license changes, tags and release remain subject to separate authorization.
No private interview material was read or restored. No push, PR, merge,
tag, release, plan upgrade or AWS resource creation is part of this gate.

## RP-12C successor — 2026-10-08

This RP-12A gate is historical evidence. The current Terraform lifecycle now
references owner-managed security foundations and defers Lambda/API Gateway.
See the [RP-12C gate](rp12c_gate.md) for actual successor validation and remaining
owner bootstrap/live acceptance conditions. RP-12B local evidence is preserved.
