# RP-11 — security, CI, Docker and observability

Acceptance date: 2026-10-08, America/Sao_Paulo.
Branch: `feat/rp-11-hardening`, created from the verified clean main revision
`729ce9a2a7b245f35c7750af36eeb00e148798ae`.

**RP-11 ENGINEERING: PENDING** — genuine Docker image build is still required by
engineering criterion 9. No Docker executable was found on PATH or at the
standard Docker Desktop location. The container definition has only static local
validation; the successful Python wheel build is not a Docker build.

**RP-11 FULL GATE: PENDING REMOTE CI** — no feature PR or remote checks were
created. Actual image build/startup, Windows/Linux checks on that feature PR,
critical status checks and verification of branch protection remain outstanding.
No push, merge, RP-12 or RP-13 work was performed.

## Local validation

| Check | Result |
| --- | --- |
| Final portable regression suite | PASS: 245 tests in 282.45s; original 219 preserved, 26 added |
| Final coverage | 88.15% combined line/branch coverage; minimum 85% |
| Ruff | PASS |
| Strict mypy 2.4.0 | PASS, four explicitly scoped boundary modules |
| pip compatibility | PASS, no broken requirements |
| Dependency scan | PASS, 123 pinned packages, zero skips, zero known vulnerabilities |
| Secret scan | PASS, all tracked files and non-ignored new files |
| Pre-commit configuration | PASS, validated with an ignored workspace cache |
| Wheel and sdist build | PASS, both actually built; archive contents inspected |
| Compose/workflow static inspection | PASS; not a Docker runtime test |
| Running synthetic API/UI | PASS on isolated ports 8011/8511 |
| Shutdown | PASS, validation ports closed; launcher lifecycle event observed |
| Real Gold and 45 frozen artifacts | PASS, no changed hashes |
| Git diff checks | PASS |

The original 219-test baseline was measured from a separate ignored export of
revision `729ce9a`, not from a changing working tree: **219 passed in 146.64s**,
**87.6274% combined line/branch coverage** across `src/retailpulse` and `app`.
The enforced threshold is **85%**. No coverage exclusions or failure suppressions
were added to reach it. New tests cover readiness, wrong-mode isolation,
correlation/redaction, actual simultaneous slot exhaustion/recovery, cache copy
isolation, read-only/external-access restrictions, deadlines, snapshot tampering,
platform launcher flags, lifecycle events, scanner tripwires and complete audit
scope. Original test files remain unchanged. The final verification script passed
lint, scoped types, all tests, coverage, pip compatibility and Git diff checks.
Two non-failing deprecation warnings remain in Starlette/HTTPX and MLflow/SQLAlchemy.
See the [coverage summary](rp11/coverage.json) for measured per-file results.

Coverage includes application code, not developer scripts. Existing CLI
subprocesses and browser execution are outside in-process coverage. Important
uncovered areas include CLI dispatch, client network failures and OS process
cleanup branches. Those are not represented as fully covered by mocks. Genuine
launcher/API/UI acceptance supplements the unit tests. Existing tiny synthetic
model fits remain in the original regression suite; no real model training job,
download or frozen-artifact regeneration was added.

## Security results and remediation

pip-audit **2.10.1** initially returned 12 toolchain records representing six
unique pip 25.0.1 advisories (five medium, one low). pip was updated to **26.2.1**;
all RP-10 application dependency versions were preserved. A complete final scan
covered all **123** exact package/version pins with no skips and no known findings.
The nested requirements include was not expanded in the scanner's no-resolution
mode; both files are now explicit inputs and a tested scope assertion fails any
incomplete report. No unavailable or partial scan is counted as final acceptance.

detect-secrets **1.5.0** found 142 reviewed false positives: public checksums and
Power BI object identifiers, plus one deliberately invalid loopback credential
test. Six of those checksums protect the packaged synthetic tables. Exceptions
are exact path/type/fingerprint entries; all default detectors remain enabled.
The baseline file itself is scanned; its fingerprint metadata is separately
counted. No real credentials were found, and a new unexpected finding fails CI.
This is a working-tree scan, not a historical Git scan.

See the complete [dependency report](rp11/dependencies.json),
[sanitized secret report](rp11/secrets.json) and [security findings](../security.md).
Advisory databases cannot prove absence of unknown issues; container OS packages
were not scanned locally because no image was built.

## Observability and real portable acceptance

`/health` retains its RP-10 contract. `/ready` returns 200/degraded when the selected
dataset and deterministic tools work but Ollama is unavailable; missing data returns
503/unavailable. It never swaps real data for synthetic data. Discovery is not
represented as a successful model generation.

Actual synthetic API/UI checks returned **378 units** for SYN_A over the packaged
period, grounded in the approved KPI result and using
`deterministic:explicit_offline_mode`. They also rejected a malicious SQL request.
See [portable acceptance](rp11/portable.json). One concurrent run during the full
test suite reached the unchanged five-second query budget and returned a sanitized
504 `query_timeout` at 5540ms. Repeating without the competing suite passed;
timeouts were not enlarged or disabled to obtain acceptance.

Structured events expose only closed operational fields. User questions, headers,
credentials, provider responses, SQL/filter arguments and exception text are absent.
The API generates correlation UUIDs and safe response headers. Existing traces now
keep `validated_filters` empty while typed API results preserve complete scope.
Actual sanitized examples are in [log_examples.jsonl](rp11/log_examples.jsonl).
Windows launcher shutdown was observed, and both validation ports were closed.

## Container and remote limitations

The digest-pinned Python 3.12 image installs 74 pinned runtime dependencies,
runs as UID 10001 and packages code plus synthetic data only. Compose publishes
localhost ports, drops capabilities, disallows privilege escalation and provides
disposable writable tmpfs mounts over a read-only root. Real mode is rejected.
No Dockerized Ollama, database service, AWS account or external AI API is required.

The existing `validate.yml` was extended, not duplicated: Windows/Linux validation,
coverage, exact dependency audits, full-tree secret scanning, Python package build,
and a separate actual container build/startup/non-root/API/UI check. Critical
commands are fail-fast. Actions are pinned by verified commit IDs, permissions are
read-only, checkout credentials are not retained, and only sanitized reports are
published. The definitions have not run remotely in this stage.

Follow [developer workflow](../developer_workflow.md) for local commands and
[manual branch-protection instructions](../security.md#ci-and-manual-branch-protection).
Branch protection is not claimed active. Outstanding acceptance requires an
authorized future push/PR, successful required checks and a genuine Docker run.

## Protected data

All 46 protected files were compared against SHA-256 values captured before edits:
one Gold database and 45 frozen model artifacts, with no changes. Gold SHA-256:

```text
7228489a792fcf4e464014f729313c8731180621df378e31567894cccba7e620
```

See [integrity and shutdown evidence](rp11/integrity.json). Synthetic manifest
checksums were added without modifying any synthetic CSV contents. No real M5
row-level files, populated databases, private model binaries or secrets were added.
