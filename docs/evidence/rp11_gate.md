# RP-11 — security, CI, Docker and observability

Acceptance date: 2026-10-08, America/Sao_Paulo.
Branch: `feat/rp-11-hardening`, created from the verified clean main revision
`729ce9a2a7b245f35c7750af36eeb00e148798ae`.

**RP-11 ENGINEERING: PASS** — corrected Windows, Linux and genuine Docker checks
passed remotely. See the dated closure below for exact revisions and run links.

**RP-11 FULL GATE: PASS** — corrected PR and post-merge CI succeeded; the active
main ruleset was verified read-only on 2026-10-08. Its actual zero-approval review
policy is recorded explicitly. Historical failures and the original local-only
limitations below remain preserved. This closure does not validate RP-13 commits.

## Initial local validation (before the CI corrections below)

| Check | Result |
| --- | --- |
| Final portable regression suite | PASS: 245 tests in 282.45s; original 219 preserved, 26 added |
| Final coverage | 88.15% combined line/branch coverage; minimum 85% |
| Ruff | PASS |
| Strict mypy 2.4.0 | PASS, four explicitly scoped boundary modules |
| pip compatibility | PASS, no broken requirements |
| Dependency scan | PASS, 123 pinned packages, zero skips, zero known vulnerabilities |
| Secret scan | Reported PASS; incomplete on Windows due to locale decoding, superseded below |
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

The initial detect-secrets **1.5.0** run found 142 reviewed false positives: public checksums and
Power BI object identifiers, plus one deliberately invalid loopback credential
test. Six of those checksums protect the packaged synthetic tables. Exceptions
are exact path/type/fingerprint entries; all default detectors remain enabled.
The baseline file itself is scanned; its fingerprint metadata is separately
counted. That local result missed a UTF-8 document under Windows CP1252 and must
not be treated as complete acceptance. The correction below reviews six additional
provenance hashes and makes scanner decoding portable. This is a working-tree
scan, not a historical Git scan.

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
published. These definitions subsequently ran in
[Actions run 37730846032](https://github.com/sjimenezch001/retailpulse-ai/actions/runs/37730846032)
at revision `c3bd076`: the container job passed; both validation jobs failed for
the distinct causes documented below. Docker code was not changed by this fix.

Follow [developer workflow](../developer_workflow.md) for local commands and
[manual branch-protection instructions](../security.md#ci-and-manual-branch-protection).
Branch protection is not claimed active. Outstanding acceptance requires an
an authorized future push/PR and successful checks for that corrected revision
at the time of the original report; the dated closure below resolves this item.
The original container job provides genuine Docker evidence for `c3bd076` only.

## Protected data

All 46 protected files were compared against SHA-256 values captured before edits:
one Gold database and 45 frozen model artifacts, with no changes. Gold SHA-256:

```text
7228489a792fcf4e464014f729313c8731180621df378e31567894cccba7e620
```

See [integrity and shutdown evidence](rp11/integrity.json). Synthetic manifest
checksums were added without modifying any synthetic CSV contents. No real M5
row-level files, populated databases, private model binaries or secrets were added.

## CI corrections — 2026-10-08

The linked run's job conclusions and failed steps were independently checked using
the public GitHub Actions API. Windows failed the verification step; Ubuntu failed
the security step after its tests passed; the container job succeeded. The reported
Windows totals were **187 passed, 1 failed, 57 setup errors**, with **71.95%** coverage.
Those setup failures prevented dependent tests from running; the coverage threshold
was not the root cause and remains **85%**.

### A. Git checkout changed authenticated CSV bytes

The six committed synthetic CSV blobs contain LF newlines and match every SHA-256
in `src/retailpulse/api/synthetic/manifest.json`. Without attributes, a Git checkout
with `core.autocrlf=true` converts every CSV to CRLF. That changes all six hashes
before `portable_database()` reads them, correctly causing integrity rejection.
The local repository used `core.autocrlf=input`, hiding this checkout difference.

The regression uses isolated real Git repositories and `checkout-index`, with
`core.autocrlf=true` / `core.eol=crlf` and `false` / `lf`. An unprotected control
file proves that Git actually performs the requested conversion. It reproduces the
original Windows rejection, then verifies exact byte equality and full SHA-256
equality against the manifest after the fix in both checkout modes.

| Synthetic CSV | Original LF bytes | Unprotected CRLF bytes | After fix, both modes |
| --- | ---: | ---: | --- |
| `mart_sales_daily.csv` | 52,735 | 52,988 | Exact bytes and manifest SHA-256 match |
| `dim_store.csv` | 66 | 70 | Exact bytes and manifest SHA-256 match |
| `dim_product.csv` | 73 | 76 | Exact bytes and manifest SHA-256 match |
| `pipeline_metadata.csv` | 276 | 278 | Exact bytes and manifest SHA-256 match |
| `fact_forecast.csv` | 56,809 | 57,272 | Exact bytes and manifest SHA-256 match |
| `metric_definitions.csv` | 1,196 | 1,204 | Exact bytes and manifest SHA-256 match |

`.gitattributes` applies `-text` only to `/src/retailpulse/api/synthetic/*.csv`,
preserving their exact committed bytes. The packaged manifest uses `text eol=lf`
because its bytes also determine the database cache identity. Its existing local
CRLF copy was restored to the unchanged LF Git blob. No CSV, manifest checksum,
business figure, loader logic or coverage configuration was changed. Both protected
checkout modes create the same snapshot identity and return **378 units** for SYN_A.
These are actual Git checkout tests on the local Windows host, not a claim that the
corrected revision has already passed a native Linux or GitHub runner.

### B. Six provenance hashes were absent from the reviewed baseline

Linux correctly rejected six `Hex High Entropy String` findings in
`docs/evidence/real_m5_validation.json`. Each was independently recomputed with
SHA-256 from the corresponding local file; all six matched exactly:

| Evidence line | Value provenance | Verification |
| ---: | --- | --- |
| 15 | `data/raw/m5/calendar.csv` | Exact SHA-256 match |
| 29 | `data/raw/m5/sell_prices.csv` | Exact SHA-256 match |
| 38 | `data/raw/m5/sales_train_evaluation.csv` | Exact SHA-256 match |
| 75 | Bronze run `47b8b962c868f3c60fc8`, `calendar.parquet` | Exact SHA-256 match |
| 150 | Same Bronze run, `prices.parquet` | Exact SHA-256 match |
| 193 | Same Bronze run, `sales.parquet` | Exact SHA-256 match |

The Bronze files are under `data/processed/bronze/runs/47b8b962c868f3c60fc8/`.
Only these six path/type/fingerprint exceptions were added to `.secrets.baseline`,
each with its individual provenance review. No file-wide exclusion, detector change,
credential exception or automatic baseline refresh was introduced.

The earlier Windows PASS had a separate explanation within this scanner failure:
detect-secrets 1.5.0 opens text with the process's default encoding and silently
ignores decoding errors as binary files. This UTF-8 evidence document fails CP1252
decoding at byte 24,193 (`0x9d`). Running the unchanged scanner with `-X utf8`
reproduced exactly the six Linux findings before the baseline correction.
`scripts/scan_secrets.py` now re-executes its CLI in UTF-8 mode when necessary,
keeping all default detectors and the existing exact exception checks.

Five scanner regressions execute the real CLI starting with UTF-8 mode disabled.
They require all six reviewed hashes to be detected and accepted, and fail for a
new disposable credential in the same document, a changed unreviewed checksum,
an approved value in another file, or an exception without a review reason.
Reports are checked for credential redaction. The four checkout regressions and
these five scanner regressions add **nine** tests.

### Corrective validation

| Check | Corrected result |
| --- | --- |
| Complete suite via `python scripts/verify.py` | PASS: **254 passed**, 0 failures, 0 errors, two existing deprecation warnings, **171.00s** |
| Combined line/branch coverage | **88.1530%**, unchanged **85%** minimum; no exclusions added |
| Actual Git checkout regressions | PASS: four cases, including original Windows failure and both corrected checkout modes |
| Real secret scanner regressions | PASS: five cases, including four required rejections |
| Ruff | PASS |
| Scoped strict mypy | PASS, four modules |
| `pip check` | PASS, no broken requirements |
| Dependency audit | PASS: **123** pinned packages, zero skips, zero known vulnerabilities |
| UTF-8 secret scan | PASS: **148** reviewed findings, **0** unreviewed; only six new exact exceptions |
| `git diff --check` | PASS |
| Gold and frozen model artifacts | All **46** pre-fix SHA-256 values and the protected file set unchanged |
| Synthetic CSVs and manifest | Exact equality with the original committed Git blobs |
| Docker implementation | Unchanged; original remote container job passed |

See the machine-readable [corrective evidence](rp11/ci_corrections.json).
The initial reports linked earlier remain historical evidence, including the
incomplete Windows secret-scan result. Application behavior, pipeline logic,
checksum enforcement, tool allowlists, database protections, dependency versions,
Gold and frozen artifacts were preserved. Remote checks for this corrected
revision were pending at the time of that local fix; no push or merge was performed
by that correction task. The following closure records the subsequent remote work.

## Verified closure — 2026-10-08

RP-13 documentation review queried the public GitHub API read-only and confirmed:

| Evidence | Observed state |
| --- | --- |
| [PR #11](https://github.com/sjimenezch001/retailpulse-ai/pull/11) | Merged at 2026-10-08 05:55:03 UTC; resulting main revision `593dc50` |
| [Corrected PR run 37732985345](https://github.com/sjimenezch001/retailpulse-ai/actions/runs/37732985345) | Revision `bb2a0c9`, completed/success; Windows, Ubuntu and container each succeeded |
| [Post-merge run 37734804078](https://github.com/sjimenezch001/retailpulse-ai/actions/runs/37734804078) | Revision `593dc50`, completed/success; Windows, Ubuntu and container each succeeded |
| [Ruleset 24699291](https://github.com/sjimenezch001/retailpulse-ai/rules/24699291) | Active, default branch, PR required, linear history, deletion/force-push blocked, strict up-to-date required checks |

Required check names are exactly `validate (ubuntu-latest)`,
`validate (windows-latest)` and `container`. Container success includes the existing
actual Compose image build, startup, API/UI acceptance and non-root checks.
This supersedes the historical Docker/remote-CI blockers; it is not a local Docker
Desktop installation or a claim that the failed run succeeded.

The ruleset requires **zero approvals**. Stale-review dismissal, code-owner review,
last-push approval and conversation resolution are disabled. The public API did
not enumerate bypass actors, so bypass absence is not claimed. The earlier
one-approval recommendation was not the configuration actually adopted. The
verified protection and successful required checks close RP-11 under that recorded
policy. Settings were not modified or destructively tested during this review.

The original failed run `37730846032`, its LF/CRLF and UTF-8 causes, all correction
evidence and earlier local reports remain intact. RP-13 starts separately from
the synchronized clean `593dc50` main revision. Its unpublished commits require
their own checks before any future merge.
