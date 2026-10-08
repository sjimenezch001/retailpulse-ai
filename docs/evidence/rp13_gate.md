# RP-13 portfolio packaging gate

Updated: 2026-10-08. Current localization branch: `docs/rp13-demo-localization`,
created from clean synchronized main `b6622e3` after a fetch and exact local/remote
comparison. The owner approved the English recording. See the
[dated localization update](#demo-localization--2026-10-08) for current media status.
The packaging and privacy sections below retain their historical revision context.

Initial packaging date: 2026-10-08. Branch: `feat/rp-13-portfolio`.
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
| GENUINE ENGLISH DEMO VIDEO | COMPLETE / OWNER APPROVED — original 147.517067 seconds preserved |
| SPANISH / PORTUGUESE EXPORTS | COMPLETE / TECHNICALLY INSPECTED — 149.813500 / 147.425333 seconds; owner review not claimed |
| INDEPENDENT HUMAN QUICK START | PENDING — deferred by owner |
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
been committed, uploaded or published. Owner review was pending at initial capture;
the owner has now approved its content and presentation. Public hosting remains
unauthorized; see the dated localization update.

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

1. Independent human quick start remains **PENDING, deferred by the owner**.
   When resumed, record revision, OS, Python, commands, physical Ctrl+C and outcomes
   with the tester's consent.
2. The existing English video's content and presentation are owner-approved.
   Owner review of the new localized exports is not claimed. Review remaining
   portfolio wording and choose the missing code license.
   No root LICENSE or project license metadata currently grants code permissions;
   competition-data rights are separate.
3. Authorize a future PR/push, obtain candidate CI, and approve coordinated version,
   tag/release and optional video hosting steps. Verify final public links and
   repository pinning only after authorization.

See [draft notes](../release_notes_v1.0.0.md) and the
[release checklist](../release_checklist.md). These open checkpoints keep
**RP-13 FULL GATE: PENDING**. Neither a published release nor independent human
acceptance is implied by packaging success.

## Demo localization — 2026-10-08

The owner approved the existing English video and deferred independent human
quick-start verification, which remains **PENDING**. A new branch,
`docs/rp13-demo-localization`, was created from verified clean, synchronized main
`b6622e3`; no merged feature branch was reused. Documentation remains in English
except the intentionally localized public captions. Private preparation material
was neither restored nor linked.

| Export | Actual duration | Bytes | Format | Decoded samples |
| --- | --- | --- | --- | --- |
| Original English, preserved | 147.517067 s | 1,874,308 | MP4/AVC, 1600 × 1120, silent | Existing source inspected |
| Spanish UI / Spanish captions | 149.813500 s | 10,789,833 | MP4/AVC, 1600 × 1120, silent | 1,499 of 1,499 |
| English UI / Brazilian Portuguese captions | 147.425333 s | 10,813,947 | MP4/AVC, 1600 × 1120, silent | 1,474 of 1,474 |

The new videos are ignored local files at `artifacts/rp13/retailpulse-demo-es.mp4`
and `artifacts/rp13/retailpulse-demo-pt-BR.mp4`. Tracked deliverables are
[Spanish SRT](../demo_captions.es.srt), [Brazilian Portuguese SRT](../demo_captions.pt-BR.srt)
and the [validation record](rp13/localization.json). The original English MP4 and
English SRT were preserved byte-for-byte, including their original timing.

Spanish was captured from the functioning existing UI on isolated ports 8017/8517,
using Gold read-only and an explicitly deterministic provider. The supported Spanish
April 2016 question was typed into the app; the genuine result shows **25.307**,
CA_1, its period, Gold source, grounding and
`deterministic:explicit_offline_mode`. The visible **0.18 s** is this offline
request's actual displayed duration, not a model latency claim. No Ollama inference,
model warm-up, training, raw-data build or new evaluation occurred. Browser renders
and interactions were recorded directly; no translated answer was inserted into an
image. Both owned capture attempts shut down their own servers; the final shutdown
returned zero, reaped eight descendants and released both ports. No user demo was
interrupted.

The first capture succeeded in the app but its recording harness expected a
browser-visible API response, whereas Streamlit calls the API server-side. The
local harness was corrected to verify the rendered result and the walkthrough
was captured again. No product code or regression test was changed. Existing UI
limitations remain visible: the initial selected "All stores" / "All departments"
chips retain English until interaction, after which they display Spanish. Technical
names and existing Spanish model display labels were not edited.

No caption-free original English recording was available. The Portuguese export
copies only its application area, coordinates (0, 0, 1600, 1000), and replaces the
separate bottom 120-pixel caption band. Spanish uses fresh caption-free footage.
Neither export covers application content or stacks localized text over English
captions. Portuguese is a caption language only; the UI remains English. There is
no audio, narration or voice cloning. Local Chrome tools were used without paid
services, cloud deployment or external model/browser downloads.

Complete final MP4 sample streams were demuxed and decoded with Chrome WebCodecs,
including a final decoder flush: zero errors and zero unprocessed samples. Each
frame's band matched its expected localized cue; all 14 cues appeared once in
order in each export. An initial real-time Portuguese playback observer dropped
30 presentation frames while the Spanish encoder was running; it was not accepted
as complete validation. The subsequent full sample-by-sample software decoding
processed all 1,474 frames successfully. That playback observation is retained in
the local audit, rather than represented as a zero-drop playback run.

All six story scenes and all 28 caption bands were visually inspected from decoded
final exports. Text fits inside the separate band; historical-data, partial
`revenue_proxy`, deterministic-provider and scope notices remain visible. Figures
reconcile to the existing aggregates and frozen metrics: 4,530,250; 1,477,827;
25,307; WMAPE 74.825958% / 79.482353%; RMSE 2.431177 / 2.361194. Localized
punctuation changes no value. The Windows/Linux/Docker caption describes prior
recorded CI evidence, not a new remote run for this branch.

Each new UTF-8 SRT is timed from its own final export's observed caption transitions,
with less than 1 ms rounding. Spanish ends at 149.813 s; Portuguese at 147.425 s.
No cue extends beyond its video. These companion SRTs should not be enabled as an
extra overlay over the already burned-in band. Video timing is variable, about
10 encoded frames per second; these are screen walkthroughs without audio.

| Localization repository verification | Actual result |
| --- | --- |
| `python scripts/tasks.py verify` | PASS; 254 tests, zero failures, 2 existing warnings, 357.23 seconds |
| Combined line/branch coverage | 88.15303430%; unchanged minimum 85% |
| Ruff / scoped mypy / pip check | PASS / PASS (four modules) / PASS |
| `python scripts/tasks.py security` | PASS; all 123 pinned packages, zero skips or known vulnerabilities |
| Secret scan | PASS; all detectors active, 148 unchanged exact reviewed entries, zero unreviewed findings |
| Internal Markdown links, images and anchors | 215 checked; zero errors |
| `git diff --check` | PASS |
| Preservation after all tests | 48 SHA-256 comparisons unchanged: Gold, all 45 frozen artifacts, original MP4 and English SRT; frozen file set unchanged |

Only documentation and the two new caption tracks changed. Application behavior,
metrics, dependencies, tests, coverage configuration and scanner exceptions remain
unchanged. The two existing warnings concern Starlette/HTTPX and MLflow/SQLAlchemy.
A fresh process-scoped pytest base directory avoided the earlier Windows temporary
directory permission issue. Pytest interpreted Windows path backslashes through
its options parser; the generated directory remained inside this workspace and
was moved into ignored task evidence after the suite finished. No user directory
or permissions were changed. The local helper now spells that path with forward
slashes. This was temporary test-output placement, not a test failure or bypass.
The independent human quick start and remote CI were not rerun.

Production and technical inspection are complete. Independent human quick start
remains **PENDING, deferred by the owner**. New localized owner approval is not
claimed. Public video hosting, code license, coordinated version change and
release publication still require separate authorization. No push, merge, upload,
tag, release, license/version change or AWS work was performed.
