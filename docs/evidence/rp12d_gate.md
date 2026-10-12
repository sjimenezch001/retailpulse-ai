# RP-12D gate: live AWS reconciliation passed; closeout pending

Evidence update: 2026-10-11. This is an offline review of genuine owner-executed
AWS receipts, not another deployment/query session. Earlier RP-12A/C gates are
historical offline-preparation evidence and remain preserved.

| Item | Status | Evidence / boundary |
| --- | --- | --- |
| Real Glue 5.0 Spark execution | PASS | Successful JobRunId in [public evidence](rp12d_live_validation.json); 125 execution seconds, 250 DPUSeconds |
| Actual five curated Parquet datasets | PASS | Every schema/row/value matched the immutable synthetic reference; hashes/version records retained locally |
| Both completion markers | PASS | `_complete.json` and `_metric_candidate.json` matched run, inputs and metric reference |
| Six real Athena SELECTs | PASS | Six SUCCEEDED/expected-result matches; actual IDs, 3,165 total scanned bytes and per-query latency retained |
| Synthetic business reconciliation | PASS | 252 facts, 1,386 units; SYN_A 378, SYN_B 462, SYN_C 546; joins and quality verified |
| Botocore ZIP failure resolution | PASS | Offline reproduction, separate versioned application-only ZIP, then genuine Glue success; original failed run retained |
| Athena response-validator resolution | PASS | Two observed representation differences only, 21 offline tests, corrected-file/patch identity verification and subsequent six real PASS results |
| Infrastructure ownership | RECORDED | Seven Terraform resources, one direct Boto3 job and two Console groups; state serial 20 unchanged |
| Local preservation archive | PASS | 699 members re-read/SHA-256 verified; corrected ZIP separately copied; 125 protected-file hashes unchanged |
| Documentation checks | PASS | Ruff and whitespace checks; 91 local links resolved; no new-document secret finding |
| Current full working-tree secret scan | FAIL / separate existing fixture | One AWS-key-pattern finding at tests/aws/test_cli_diagnostics.py:31, a pre-existing untracked file; left untouched, detectors/baseline unchanged |
| Raw remote output/log byte retention | PENDING / CLEANUP HOLD | Results exist locally as JSON; actual remote Parquet, CSV/metadata and event-message exports need separate preservation review |
| Current gross costs / settled billing | NOT VERIFIED | Execution telemetry is not an invoice; owner budget/credit observations are separately labeled |
| Historical operator trust continuity | NOT VERIFIED | No authentic historical baseline; current MFA/foundation checks do not prove continuity |
| Serving publication / endpoint | NOT EXECUTED | No `serving/` metric, Lambda/API Gateway or Redshift workload |
| Cleanup / foundation retirement | NOT AUTHORIZED / NOT EXECUTED | [Ownership-aware proposal](../aws_cleanup_plan.md), separate approval for each stage |
| Publication / license / release | PENDING | Local documentation proposals only; no push, release, tag, upload or license change |

The full [walkthrough](../aws_live_demo.md) distinguishes actual cloud execution
from synthetic business data and explains resolved engineering incidents.
It does not claim M5 processing on AWS, cloud model evaluation, commercial
uplift or production customers. Independent human quick-start verification
remains PENDING, deferred by the owner under the separate RP-13 acceptance.

Private original receipts, state/plans, ownership/version ledger and hashed
archive are local under `artifacts/rp12d/portfolio-closeout-20261011/`. Public
evidence is an allowlisted projection excluding credentials, caches, account
numbers, full IAM ARNs, account-specific bucket URIs and local user paths.
Source/prepared seals, Gold and all frozen model assets remain unchanged.

Cleanup is held until valuable remote files/logs have a reviewed retention
decision and a fresh exact ownership inventory. No destructive command, AWS
call or Terraform operation was executed to prepare this gate.
