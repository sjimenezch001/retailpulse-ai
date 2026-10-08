# RP-13 portfolio packaging gate

Date: 2026-10-08. Branch: `feat/rp-13-portfolio`.
Base: clean synchronized main `593dc5034b629beb11045e73b5a8bc0f34317b09`,
verified against the public GitHub main commit before branching.
The unpublished packaging commits were reconstructed from this published base
to separate personal preparation from the public portfolio. Original revision and
recovery records are retained privately. Application code, dependencies, tests and
runtime configuration remain identical; replacement commits have no remote CI result.

| Gate | Current status |
| --- | --- |
| RP-13 PACKAGING | PASS |
| CLEAN-ENVIRONMENT REPRODUCTION | PASS — isolated automated reproduction, with terminal limitations below |
| GENUINE DEMO VIDEO | COMPLETE — 147.517067 seconds measured; 150-second script |
| INDEPENDENT HUMAN QUICK START | PENDING |
| RELEASE v1.0.0 | PREPARED / NOT PUBLISHED |
| RP-13 FULL GATE | PENDING |

This packages a personal portfolio. No product feature, UI redesign, metric change,
real-data regeneration or real-model training was performed. English/Spanish UI,
light/dark themes, read-only protections and the 85% coverage threshold remain
unchanged. RP-12 AWS is optional and deferred. No push, merge, release, tag, social
post or branch-protection change was performed.

## Evidence and deliverables

The [English README](../../README.md) and [Portuguese summary](../../README.pt-BR.md)
present the same bounded claims. The [architecture](../architecture.md) separates
build operations from read-only serving and documents analytical grains.

The [portfolio evidence index](../portfolio_evidence.md) maps each headline number
to its recorded source. The [RP-11 dated closure](rp11_gate.md#verified-closure--2026-10-08)
records read-only verification of merged PR #11, both successful remote runs and
the active ruleset. The earlier failed run and corrective reports are preserved.
Remote success applies to those revisions, not new local RP-13 commits.

Historical evidence confirms 4,530,250 observed pilot units; test WMAPE
74.825958% versus 79.482353%, improved MAE but worse RMSE; and 36 curated expected
assistant outcomes comprising 22 validated Ollama calls, 14 preflight outcomes and
zero fallback. These are earlier frozen measurements, not newly trained models,
universal assistant accuracy or measured commercial gains.

The active ruleset requires Windows, Linux and container checks, strict up-to-date
checks and a PR. It requires zero approving reviews; no stronger policy is implied.
Personal practice material is maintained outside the public repository. Technical
explanations, design trade-offs, model limitations and security evidence remain
in their public technical documents. Release documents leave package/version
assertions at `0.1.0` and publication explicitly pending.

## Clean-environment reproduction

This was an **isolated automated reproduction on the available Windows machine**,
not another person's independent acceptance. See the sanitized
[installation/runtime/shutdown report](rp13/reproduction.json) and the genuine
[synthetic assistant capture](rp13/synthetic_assistant.png).

Before privacy reconstruction, an independent Git clone with
`--no-local --no-hardlinks` was checked out detached at the original packaging
candidate under ignored `artifacts/rp13/clean_checkout`. Its exact original
revision is retained privately. This is historical execution evidence, not a
claim that installation was repeated for the replacement commits. Runtime source
files match published main `593dc50` and the reconstructed candidate. The clone
had no copied `.venv`, `.env`, real raw data,
real Gold, model artifacts or model cache. A new environment was created with
base **Python 3.12.10**, then the supported setup command installed the pinned
dependencies. Empty profile/AppData directories, `PIP_CONFIG_FILE=nul` and
`PIP_NO_CACHE_DIR=1` isolated application configuration and package caching.

The original clone/detached-checkout commands are retained in local execution
records. The executed setup/startup sequence inside that isolated checkout was:

```powershell
# In the checkout, invoke the verified base Python 3.12.10 executable:
# <base-python.exe> -m venv .venv
.\.venv\Scripts\python.exe scripts/tasks.py setup
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m retailpulse demo --mode synthetic --provider deterministic --api-port 8013 --ui-port 8513
```

The documentation's `py -3.12` discovery depends on this host's per-user Python
registration, which was absent from the deliberately empty profile. The verified
base interpreter created the new venv directly; the existing project venv was
not reused. Installation completed in **602.203 seconds** and pip reported no
broken requirements. Internet was needed for installing packages.

| Acceptance | Actual result |
| --- | --- |
| Synthetic startup | PASS, API 8013 / Streamlit 8513, real Gold unavailable |
| `/health`, `/ready` | Both HTTP 200; synthetic dataset available |
| Overview API and browser | 1,386 synthetic units and rendered chart |
| Forecast API and browser | Two illustrative comparison models and rendered chart |
| Assistant API and browser | SYN_A, all observed dates: 378 units; grounding validated |
| Provider | `deterministic:explicit_offline_mode`; live-provider success false |
| Browser | Installed Chrome 154.0.8037.98, three tabs checked, no page errors |
| Launcher shutdown path | Exit 0, shutdown event, all seven descendant processes reaped |
| Cleanup | Ports 8013/8513 and video ports 8014/8514 closed; no user demo interrupted |

The installed host Ollama service was discoverable by readiness, but no model
inference or cache was used to obtain the synthetic answer. This is not a claim
that Ollama was uninstalled from the machine. Chrome's observer process needed
native Windows profile paths for OS cryptography; Playwright still used a new
temporary browser profile, and the application kept its isolated profile.

Initial browser assertions were ambiguous because both the metric card and its
evidence table contain `378`. Scoping the selector to the answer metric passed;
no application behavior or regression test was changed to satisfy the harness.

The automated terminal did not deliver physical Ctrl+C to the initial launchers.
Those owned sessions were explicitly cleaned up and are **not** counted as graceful
shutdown proof. A fresh clean-environment CLI run then received a Python
SIGINT/KeyboardInterrupt through an external harness. The unchanged launcher
printed its normal stopping message, emitted `shutdown`, returned zero, reaped its
children and released the ports (8.578 seconds including port probes). This proves
the application's interrupt cleanup path. Physical keyboard delivery and an
independent person's full quick start remain pending.

## Demo recording

The [existing script](../web_demo.md#150-second-product-walkthrough) was refined to
the required six-part, 150-second structure; [English captions](../demo_captions.en.srt)
were used in the finished recording. No voice or live-model response was fabricated.

**Completed recording:** a genuine working-app walkthrough was captured on isolated
real-mode ports 8014/8514, using existing Gold read-only. It shows the overview
and CA_1 filter, architecture, frozen forecast comparison and the grounded
25,307-unit answer. The finished local, ignored file is
`artifacts/rp13/retailpulse-demo-150s.mp4`: **147.517067 seconds**, **1600 × 1120**,
**1,874,308 bytes**, MP4/AVC. The capture schedule was 150 seconds; actual encoded
duration is reported rather than rounded up.

Continuous genuine browser frames were recorded through Chrome Canvas
MediaRecorder with a separate English caption band. No application figures,
answers or screenshots were fabricated. Playback was decoded and inspected at
30, 61, 90, 119 and 144 seconds; [media evidence](rp13/video.json) records the
actual actions and timing. The earlier first capture was superseded locally.

This recording uses **explicit deterministic offline mode**, with **zero Ollama
calls**, no model warm-up and no audio or synthesized voice. The visible answer
latency is an offline request measurement, not LLM inference or video duration.
Earlier RP-09 live-model evidence remains separately labeled. The MP4 has not
been committed, uploaded or published; owner review and hosting approval remain.

## Initial packaging validation and preservation

The table below preserves the initial packaging run before privacy separation.
The [validation summary](rp13/validation.json) records the new checks on the
reconstructed candidate; the table here preserves the earlier run. Historical browser/installation
evidence is not represented as a new execution.

| Command or check | Result |
| --- | --- |
| `python scripts/tasks.py verify` | PASS; 254 tests, zero failures, 409.94 seconds |
| Combined line/branch coverage | 88.15303430079156%; required minimum 85% |
| Ruff / scoped strict mypy / pip check | PASS / PASS (four modules) / PASS |
| `python scripts/tasks.py security` | PASS; all 123 pinned packages audited, zero skips or known vulnerabilities |
| Secret scan | PASS; 319 files, all detectors retained, 148 exact reviewed exceptions unchanged, zero unreviewed findings |
| `python scripts/tasks.py build` | PASS; wheel and sdist at unchanged version 0.1.0 |
| Archive inspection | Six synthetic CSVs each; no real rows, database, model binaries, PBIX or video |
| Markdown/image/anchor checks | PASS; 224 internal links at that time, no errors; English/Portuguese headline claims agree |
| Documentation commands | Supported task/CLI commands inspected; synthetic setup/startup exercised above; real build commands not executed |
| `git diff --check` | PASS |
| Gold + frozen artifacts | All 46 SHA-256 values and the protected file set unchanged: one Gold database, 45 artifacts |

The suite retained two existing deprecation warnings (Starlette/HTTPX and
MLflow/SQLAlchemy). A network-restricted dependency-audit attempt failed; the
complete audit passed when rerun with network access. No partial scan counted as
acceptance. No tests, coverage exclusions, dependency versions, Docker
code or scanner exceptions were changed. This is a current-tree secret scan,
not a Git-history scan. Docker execution is evidenced by the earlier remote
workflow; no local Docker installation or RP-13 remote run is claimed.
Local raw data, populated databases, frozen models, PBIX and video remain excluded.

## Privacy separation — 2026-10-08

Read-only remote inspection verified the expected published main, no published
RP-13 branch, and no original packaging commit reachable from any advertised
branch or pull-request ref. GitHub returned "No commit found" for both original
packaging revisions. Published history and main were left unchanged.

Before reconstruction, byte-identical external private copies were verified by
SHA-256. A complete Git bundle was verified, fetched into a separate bare recovery
repository, and checked with `git fsck --strict`; original document blobs matched.
Recovery details remain private. No backup branch or tag was created.

Only unpublished local RP-13 commits are rebuilt. Narrow root-anchored ignore
rules protect the two personal document paths; public walkthroughs, captions and
technical evidence remain. The [privacy audit](rp13/privacy_separation.json) verifies
all reachable trees and objects, removal of original private-containing ancestors,
replacement messages and the limited public-tree differences. No new personal
practice content was copied into public files. Gold, all 45 frozen artifacts and
the ignored demo MP4 retain their exact hashes. The rebuilt wheel and sdist
exclude personal documents and local-only data/media.

The reconstructed public candidate `ab1722b` passed the required
checks below. The final follow-up commit only records public evidence and receives
another complete secret/link/whitespace check. Both replacement commit messages
and outgoing ancestry are checked again after committing. No remote CI result is
claimed for either unpublished replacement commit.

| Cleanup validation | Actual result |
| --- | --- |
| `python scripts/tasks.py verify` | PASS; 254 tests, 2 existing warnings, 210.30 seconds |
| Combined coverage | 88.15303430%; unchanged minimum 85% |
| Ruff / scoped mypy / pip check | PASS / PASS (four modules) / PASS |
| `python scripts/tasks.py security` | PASS; 123 packages, zero skips or known vulnerabilities; all secret detectors active |
| Final secret scan | PASS; 318 files, 148 unchanged exact reviewed entries; zero unreviewed findings |
| `python scripts/tasks.py build` | PASS; wheel/sdist 0.1.0; private documents and local-only data/media absent |
| Internal Markdown links and images | 203 checked; zero errors |
| `git diff --check` | PASS |
| Preservation | Gold, 45 frozen artifacts and MP4 unchanged; 47 SHA-256 comparisons |
| Public/private history boundary | PASS; private paths/blobs absent from reachable history; original private-containing commits are not ancestors |

The initial default-temp attempt failed with 100 tests passing and
154 setup errors because Windows denied access to an existing pytest temporary
directory. Three diagnostic tests and then the full task passed after setting
process-scoped `PYTEST_ADDOPTS` to a fresh, ignored `--basetemp` under `artifacts/rp13/`.
That initial failure is retained in the validation record. No application/test
code, dependency, threshold, scanner detector or existing directory permission
was changed. The earlier clean installation and video were not rerun or modified.

## Remaining owner decisions

1. Have another person complete the quick start, including physical Ctrl+C, and
   record revision, OS, Python, commands and outcomes with their consent.
2. Review the video and portfolio wording, and choose the missing code license.
   No root LICENSE or project license metadata currently grants code permissions;
   competition-data rights are separate.
3. Authorize a future PR/push, obtain candidate CI, and approve coordinated version,
   tag/release and optional video hosting steps. Verify final public links and
   repository pinning only after authorization.

See [draft notes](../release_notes_v1.0.0.md) and the
[release checklist](../release_checklist.md). These open checkpoints keep
**RP-13 FULL GATE: PENDING**. Neither a published release nor independent human
acceptance is implied by packaging success.
