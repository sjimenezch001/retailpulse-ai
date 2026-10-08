# v1.0.0 release checklist

Status: **PREPARED / NOT PUBLISHED**. RP-13 does not authorize a push, merge, tag,
release, repository-setting change or social-media post. The current package is
`0.1.0`; drafting these notes does not change it. [Gate](evidence/rp13_gate.md).

## Candidate review

- [ ] Review the final portfolio diff and approve a future PR/push explicitly.
- [ ] Confirm outgoing history contains only public portfolio material; personal
  preparation remains outside the repository, including prior outgoing commits.
- [ ] Obtain passing Windows, Linux and container checks on that candidate PR.
  Historical main success is not a substitute.
- [ ] Confirm the isolated clean-environment reproduction for the documented revision.
- [ ] Have another person clone, install, launch, ask the synthetic example and stop
  the demo; record their date, OS, Python, revision, commands and outcome with consent.
  **PENDING — deferred by the owner on 2026-10-08.**
- [x] Owner reviewed and approved the existing English recording's content and
  presentation on 2026-10-08 (147.517067 seconds). Original MP4 and English captions
  are preserved byte-for-byte.
- [ ] Owner review of the new Spanish-interface and Portuguese-captioned exports.
  Production and technical inspection are complete; see the
  [localization update](evidence/rp13_gate.md#demo-localization--2026-10-08).
  This review does not authorize public hosting or release publication.
- [ ] Check documentation consistency, image/internal links and public links after
  publication is authorized. Confirm English and Portuguese claims agree.
- [ ] Run final verification, complete dependency audit, all-detector secret scan
  and package build on the release candidate. Review exact new false positives only.
- [ ] Confirm Gold and all 45 frozen model artifacts are unchanged and remain local.

## Owner decisions and coordinated versioning

- [ ] Choose/approve a code license and add the proper file/metadata in a separately
  reviewed change. No code license is currently declared. Do not imply permission
  to redistribute competition data; real rows and data-filled binaries remain excluded.
- [ ] Approve the v1.0.0 version change only after acceptance. Coordinate
  `pyproject.toml`, `src/retailpulse/__init__.py`, the API `project_version` default in
  `src/retailpulse/api/contracts.py`, and `tests/test_smoke.py` in that future change.
- [ ] Rerun checks/build; inspect wheel/sdist contents and verify version agreement.
- [ ] After explicit authorization, merge the approved version change, verify its
  post-merge CI, then create an annotated `v1.0.0` tag at that exact reviewed commit.
  Push the tag and publish the reviewed release notes only with authorization.
- [ ] Approve public video hosting separately. Do not attach real data, models,
  populated databases or data-filled PBIX to the release.
- [ ] Verify final public release/demo/evidence links and pin the repository on the
  owner's profile if approved. No LinkedIn or other social posting is implied.

## Evidence to record

The automated [RP-13 gate](evidence/rp13_gate.md) records completed machine checks.
Leave human checkboxes open until an actual person performs them. Keep the exact
release revision, approving decision, verification results, independent tester
record and final public URLs with the release. Optional AWS work is not required
for this local portfolio and must not be introduced as an unreviewed dependency.
