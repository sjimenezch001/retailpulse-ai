# v1.0.0 release checklist

Release preparation snapshot: **2026-10-12**. Current publication status:
[GitHub Releases](https://github.com/sjimenezch001/retailpulse-ai/releases).
Baseline: `685839e7bcd3cc4ea33787c56124f9981bbcb305`, branch
`release/v1.0.0-portfolio`. I authorized local version preparation and MIT licensing.
At this snapshot, commit, push, PR, merge, tag and publication still required
my approval.
Historical [RP-13 gates](evidence/rp13_gate.md) retain their dated context.

## Completed and accepted scope

- [x] Portfolio documentation published through PRs #16 and #17. The
  [baseline CI](https://github.com/sjimenezch001/retailpulse-ai/actions/runs/38274725819)
  passed Windows, Ubuntu, container and aws-offline; it does not validate this candidate.
- [x] I authorized `1.0.0`; package metadata, Python runtime, API project
  version and the existing version test are coordinated. API identifier `rp10-v1`
  and data/schema versions are unchanged.
- [x] I approved MIT for original project code; root LICENSE and package
  metadata are configured. The copyright notice uses the established public
  project identity `sjimenezch001`, not an inferred legal name. Third-party and
  M5 data permissions are separate; real rows remain excluded.
- [x] Historical isolated automated reproduction passed; see the
  [documented procedure and limits](evidence/rp13_gate.md#clean-environment-reproduction).
  New candidate installation and smoke results are tracked separately below.
- [ ] Independent human quick-start verification: **PENDING**. Automated
  reproduction is a separate evidence category. On 2026-10-12, I authorized
  portfolio release with this check still pending; I did not mark it PASS.
- [x] English recording approved on 2026-10-08; original MP4 and English captions
  remain protected. Localized production/technical inspection is complete.

## Required candidate validation and review

- [ ] Review final diff and approve publication steps explicitly.
- [x] Confirm outgoing history and current tree contain only public portfolio material;
  private paths/blobs are absent from reachable history and no private passages were copied.
- [x] Run tests with the unchanged 85% combined coverage threshold, Ruff lint,
  configured mypy and dependency compatibility checks.
- [x] On 2026-10-12, I accepted 58 pre-existing Ruff formatting findings for
  this portfolio release. Global `format --check` remains **FAIL**; all three
  modified Python files pass and the baseline shows no new findings.
- [x] Run all-detector secret scan and the existing dependency vulnerability audit;
  retain failures or unavailable checks explicitly rather than declaring PASS.
- [x] Verify Markdown structure, internal links and English/Portuguese consistency.
- [x] Build and inspect wheel/sdist for `1.0.0`, MIT metadata, LICENSE inclusion
  and absence of restricted/private artifacts.
- [x] Install the built wheel in a clean environment and smoke-test the synthetic
  deterministic demo, including the 378-unit answer and shutdown where feasible.
- [x] Confirm Gold, all 45 frozen artifacts, datasets, evidence and approved media
  match the protected preservation baseline.
- [ ] After an authorized commit/PR, obtain Windows, Ubuntu, container and aws-offline
  CI on the exact candidate revision. Baseline CI is not a substitute.

## Publication steps requiring authorization

- [ ] Merge the reviewed candidate and verify post-merge CI before creating an
  annotated `v1.0.0` tag on that exact revision.
- [ ] Push the authorized tag and publish the reviewed
  [RetailPulse AI v1.0.0 — Portfolio Release notes](release_notes_v1.0.0.md).
- [ ] Verify final public release and evidence links after publication.

## Optional presentation work

- [ ] My review of Spanish-interface/Portuguese-captioned exports if they are
  selected for public presentation. Their technical inspection does not imply approval.
- [ ] Choose public video hosting only if desired; no upload is required for this
  source/package release. Do not attach real data, models, databases or PBIX.
- [ ] If separate English subtitles are hosted, prepare a reviewed clipped copy:
  the original last cue exceeds the approved video's duration. Preserve the original.

No additional AWS execution, platform technology, public application hosting or
social posting is required. Store final candidate validation below; retain the
exact release revision, my publication decision and final URLs when publication is authorized.

## Local candidate validation

Run on 2026-10-12 against the uncommitted local candidate. Reports remain under
ignored task artifacts; baseline CI is linked above, not attributed to these changes.

| Check | Result |
| --- | --- |
| Python tests / coverage | PASS: 440 tests, 2 existing warnings; 88.15% combined coverage, unchanged 85% minimum |
| Ruff lint / configured mypy | PASS / PASS: four configured source modules |
| Ruff formatting | PASS on the three changed Python files; FAIL globally on 58 files, all reproduced from the baseline |
| Dependency compatibility / vulnerability audit | PASS in project and clean venv; 123 pinned packages audited, zero skipped entries or known vulnerabilities |
| Secrets / privacy | PASS: 389 files scanned, zero unreviewed findings; 148 existing reviewed entries unchanged; 39 reachable commits checked for private paths/blobs |
| Markdown / internal links | PASS: structure and English/Portuguese claims reviewed; 328 links/images/anchors, zero errors |
| Version / license / distributions | PASS: runtime, health project version, wheel and sdist agree on 1.0.0; MIT metadata and LICENSE included; no restricted/private artifacts |
| Clean installation / deterministic smoke | PASS: fresh Python 3.12 venv with pinned runtime dependencies and the built wheel; API/UI accessible, SYN_A returns 378 units; API identifier remains rp10-v1 |
| Automated shutdown | PASS: launcher signal handler stopped both servers; no listeners remained. No physical keyboard or independent human check is claimed |
| Protected artifacts | PASS: 125 baseline SHA-256 values unchanged, including Gold, 45 frozen model artifacts, data and approved media |
| Candidate remote CI / publication | NOT RUN: no commit, push, PR, merge, tag or release authorized |

The pre-existing global Ruff formatting result was accepted as documented technical
debt, not reclassified as PASS. Candidate CI and publication authorization remained
open at the preparation snapshot. Independent human verification is **PENDING**;
optional media work is outside the release package validation.
