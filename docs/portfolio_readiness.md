# RP-13 express portfolio readiness

Reviewed **2026-10-12**, after the owner reviewed the
[RP-12D handoff](../RP-12D_FINAL_HANDOFF.md). The priority is a usable portfolio
for **BI / Data Analyst** applications, reusing completed work. No AWS session,
new feature, paid service, UI redesign, model training or new recording is part
of this review.

## Assets available now

| Asset | Readiness and evidence |
| --- | --- |
| English demo | Owner-approved, **147.517067 s**, 1600 × 1120, silent; original MP4 and English captions match preserved hashes |
| Spanish-interface demo | **149.813500 s**, fully decoded/inspected in prior acceptance; current hash/size match; localized owner approval not claimed |
| Portuguese-captioned demo | **147.425333 s**, English UI, prior full decode/inspection; current hash/size match; no Portuguese application UI |
| Three Power BI pages | Genuine existing captures in the [evidence index](portfolio_evidence.md#genuine-screenshot-gallery); historical data and limitations remain explicit |
| Portable local demo | Existing [clean reproduction](evidence/rp13/reproduction.json) passed: synthetic Overview, Forecast and grounded 378-unit answer; no install or browser run repeated here |
| Historical analytical proof | 4,530,250 observed pilot units; frozen WMAPE/MAE/RMSE comparison and known CA_1 answer; [claim sources](portfolio_evidence.md) |
| AWS proof and teardown | Real services, synthetic inputs; six Athena checks, 252 facts and 1,386 units; [final report](aws_teardown_report.md) distinguishes API receipts from owner observations |
| Employment copy | English CV project entry, summary, LinkedIn headline/About/post draft and interview answers prepared privately for BI / Data Analyst use; no invented work history or publication |

The three MP4s and caption files were checked against the existing preservation
baseline. Prior decode results are reused, not represented as new decoding.
The English video uses a deterministic provider; the earlier live Ollama
evaluation remains separate. No rebuild, recapture or cloud session was needed.

The original English SRT's last cue ends at **150.000 s**, beyond its
**147.517067 s** video. Both owner-approved originals remain byte-identical.
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

## Smallest remaining actions

1. **Independent quick start:** another person executes the
   [minimal check](independent_quick_start.md) on an identified candidate, including
   physical Ctrl+C. Record actual outcomes with consent. **PENDING**, not replaced
   by historical automated reproduction or this asset review.
2. **Publication candidate:** the owner reviews the local diff, including the
   previously prepared AWS documentation/source fixes and this fixture correction,
   then records an immutable candidate revision. New local evidence is not yet
   claimed visible on public GitHub. Obtain candidate Windows/Linux/container CI
   after an explicitly approved PR/push; prior main CI is historical.
3. **Public presentation:** lead with Power BI, SQL metrics and data quality;
   retain model trade-offs and the AWS synthetic-data boundary. Publish only
   reviewed source/docs/evidence. Private career copy, videos, populated databases,
   data-filled PBIX, real rows, raw AWS archives and credentials remain excluded.
4. **Owner decisions:** code license and public video hosting remain separate
   decisions. Neither a new release/tag/version nor another cloud service is
   necessary to use the existing project in applications. Do not claim a code
   license, public video URL, independent acceptance or release that does not exist.

## 48-hour execution focus

Use the private English application copy and existing approved local video
immediately. Within the next day, ask one independent person to run the short
synthetic check and record their actual result. In the remaining time, review
the candidate diff and authorize only the necessary portfolio publication step.
No new AWS run, feature, framework or full recording is on the critical path.

The portfolio is ready for owner review and local interview presentation.
Independent acceptance and candidate publication remain open. **RP-13 FULL
GATE: PENDING**; no complete MVP or published release is claimed.
