# RP-13 express portfolio readiness

Reviewed **2026-10-12**, after I reviewed the
[RP-12D handoff](../RP-12D_FINAL_HANDOFF.md). The priority is a usable portfolio
for **BI / Data Analyst** applications, reusing completed work. No AWS session,
new feature, paid service, UI redesign, model training or new recording is part
of this review.

## Assets available now

| Asset | Readiness and evidence |
| --- | --- |
| English demo | Approved by me, **147.517067 s**, 1600 × 1120, silent; original MP4 and English captions match preserved hashes |
| Spanish-interface demo | **149.813500 s**, fully decoded/inspected in prior acceptance; current hash/size match; localized approval pending |
| Portuguese-captioned demo | **147.425333 s**, English UI, prior full decode/inspection; current hash/size match; no Portuguese application UI |
| Three Power BI pages | Genuine existing captures in the [evidence index](portfolio_evidence.md#genuine-screenshot-gallery); historical data and limitations remain explicit |
| Portable local demo | Existing [clean reproduction](evidence/rp13/reproduction.json) passed: synthetic Overview, Forecast and grounded 378-unit answer; no install or browser run repeated here |
| Historical analytical proof | 4,530,250 observed pilot units; frozen WMAPE/MAE/RMSE comparison and known CA_1 answer; [claim sources](portfolio_evidence.md) |
| AWS proof and teardown | Real services, synthetic inputs; six Athena checks, 252 facts and 1,386 units; [final report](aws_teardown_report.md) distinguishes API receipts from my observations |
| Employment copy | English CV project entry, summary, LinkedIn headline/About/post draft and interview answers prepared privately for BI / Data Analyst use; no invented work history or publication |

The three MP4s and caption files were checked against the existing preservation
baseline. Prior decode results are reused, not represented as new decoding.
The English video uses a deterministic provider; the earlier live Ollama
evaluation remains separate. No rebuild, recapture or cloud session was needed.

The original English SRT's last cue ends at **150.000 s**, beyond its
**147.517067 s** video. Both originals I approved remain byte-identical.
This does not require rerecording the working MP4. If separate subtitles are
later hosted, prepare a separately reviewed copy clipped to the actual duration;
do not overwrite the original. Localized sidecars already end within their exports.

## Secret-scanner classification

The previous whole-tree finding was the deliberately fictitious AWS-shaped
input in `tests/aws/test_cli_diagnostics.py`, used to verify redaction. Its
literal alphabetic suffix and test-only use establish its provenance; it was
not read from a credential file or verified through AWS.

The minimal correction constructs the same full input at runtime and reuses it
in the negative-output assertion. The redaction test still checks the complete
key-shaped string, URL, private value and MFA example. No sanitizer, detector,
threshold, baseline exception or application behavior changed. The historical
[RP-12D handoff](../RP-12D_FINAL_HANDOFF.md) retains its earlier FAIL observation.
Current scanner/test results are recorded in the [dated gate addendum](evidence/rp13_gate.md#express-employment-readiness--2026-10-12).

## v1.0.0 candidate status — 2026-10-12

PRs #16 and #17 published the portfolio documentation. The
[published baseline CI](https://github.com/sjimenezch001/retailpulse-ai/actions/runs/38274725819)
passed four jobs at `685839e7`. This is historical CI for the baseline, not a
remote pass for the local release candidate.

I approved MIT licensing for original project code and coordinated local
version `1.0.0`. Independent human quick-start verification remains **PENDING**;
automated reproduction is a separate evidence category.
The [release checklist](release_checklist.md) records candidate checks and
remaining publication requirements. Earlier dated gates remain unchanged.

## Remaining requirements and boundaries

1. **Candidate review:** local tests, security, packaging and isolated demo checks
   passed. Global formatting still reports 58 pre-existing files, which I accepted
   as documented technical debt on 2026-10-12 without converting FAIL to PASS.
   See the [validation summary](release_checklist.md#local-candidate-validation).
   Final publication authorization is tracked separately.
2. **Candidate CI and release:** after authorized commit/PR publication, validate
   the exact candidate in CI before merging, tagging and releasing.
3. **Optional media presentation:** my review of localized exports and public video
   hosting matter only if those exports are selected for publication. Private
   career copy and preserved videos remain local; no new recording is needed.

Known analytical limits remain the forecast RMSE trade-off, historical scope,
price coverage and absence of causal/inventory evidence. The local application
and temporary synthetic AWS laboratory are intentional deployment boundaries.
CloudWatch deletion history and final billing are verification gaps documented
in the [teardown report](aws_teardown_report.md), not reopened runtime incidents.
No additional AWS run, framework or optional data platform is required for v1.0.0.

The portfolio remains usable for my review and local interview presentation.
The local release candidate is not a published GitHub Release.
