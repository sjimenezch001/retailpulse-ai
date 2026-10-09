# RP-12C gate — owner-managed foundations and bounded AWS workloads

Review date: 2026-10-08. Branch: feat/rp-12c-safe-bootstrap.
Baseline: clean main/origin-main at 2842af3e55a062016cede3cbc2f45d0418551df3.

## Status

Offline candidate: **PASS — READY FOR SEPARATE OWNER BOOTSTRAP REVIEW**.
Live deployment readiness: **NO — foundations, permissions and account eligibility unverified**.
Owner bootstrap: **PENDING / NOT EXECUTED**.
AWS live deployment and acceptance: **PENDING / NOT EXECUTED**.
Lambda, API Gateway and Redshift: **DEFERRED / DISABLED**.

## Implemented lifecycle

Owner-managed: one dedicated private/versioned/SSE-S3 bucket with reviewed TLS/
encryption/lifecycle settings; one fixed-trust Glue role, its exact inline execution
policy and immutable boundary. None is managed/imported/deleted by this Terraform.

Automated later: Glue job, database/five tables, Athena workgroup and two log groups.
Fresh read-only verification checks bucket security and exact trust/inline/boundary
documents before plan/deploy/ETL/inventory. Workload teardown preserves and verifies
the foundations and records separate owner cleanup PENDING.

No Glue security configuration or job association remains. S3 default SSE-S3,
deny-only TLS/alternate-encryption policy, private ownership and exact role
permissions protect the input/scripts/curated/temporary paths. Existing SourceAccount/
SourceArn trust is retained. Native Glue/Spark/service-context/logging compatibility
is unverified. No regional wildcard mutation or account-wide discovery is granted.

The five new operator documents omit IAM creation/mutation, bucket configuration/
deletion, Lambda/API/Redshift/EC2/RDS. Only exact Glue PassRole is granted.
Mandatory explicit denies prevent additional identity/session resource grants from
escaping reviewed action/resource/region/ownership bounds.

## Evidence and validation

The new prepared run is 5f28dec773c4cff671d22e0b, distinct from RP-12B.
Identity covers current cloud sources, SQL, pins and infrastructure.
Local synthetic references remain 55,218 input bytes, 252 facts, 1,386 units;
SYN_A 378 / SYN_B 462 / SYN_C 546. No real Gold or forecasts were uploaded.
Generated exact-account policies and private Spanish instructions are ignored
local evidence under artifacts/rp12c/. RP-12B is preserved as historical evidence.

All checks below completed locally; mock success is not AWS live acceptance.

| Check | Actual result |
| --- | --- |
| Full repository verification | PASS: 403 tests, 2 existing warnings; 275.85 seconds |
| Application coverage | 88.15%; required minimum remains 85% |
| Ruff / mypy / pip check | PASS / PASS / no broken requirements |
| Terraform fmt / backend-free init / validate | PASS; pinned lock file unchanged |
| Explicitly mocked Terraform tests | 7 passed, 0 failed; no live plan |
| Network-blocked cloud tests | 149 passed; 17.03 seconds |
| Generated IAM proposal static validation | 10 documents, 162 Allow action/resource pairs, 224 condition checks; 0 failures |
| Application dependency audit | 123 pinned packages, 0 skipped, 0 known vulnerabilities |
| Isolated AWS SDK audit | 7 pinned packages, 0 skipped, 0 known vulnerabilities |
| Secret scan | PASS: 376 files, 0 unreviewed findings; detectors/baseline unchanged |
| Package build and contents | Wheel (60 members) and source archive (85 members) built; no protected data, cloud infrastructure, local review bundles or videos included |
| Documentation local links | 242 links across 53 Markdown files; 0 missing targets/anchors |
| Protected-file preservation | All 125 recorded file hashes unchanged, including Gold, all 45 frozen model artifacts and synthetic fixtures |
| Historical RP-12B preservation | Same 61 files and exact bytes; no additions/deletions |
| Git diff whitespace | PASS for working tree and staged diff |

Ignored receipts are under artifacts/rp12c/: verify.log, cloud-validate.log,
security.log, aws-dependencies.log, build.log, final-evidence.json and the
run-specific owner-review/static-validation.json. The precise Spanish console
instructions are artifacts/rp12c/OWNER_BOOTSTRAP.es.md. Exact policies are proposed
JSON, not installed permissions. Five operator policy shards are mandatory.
Dependency versions, application behavior, license and package version are unchanged.

## Owner acceptance sequence

1. Review the Spanish guide, exact-account JSON, fixed trust/boundary and all five
   operator shards before separately approving manual bootstrap.
2. Confirm current owner identity/MFA, account/service eligibility and Free Plan;
   review budgets/credit and the gross-consumption estimate.
3. After bootstrap and separate authorization, perform STS and read-only foundation
   preflight with explicitly selected profile/account/region/environment.
4. Inspect a newly saved plan and its verified foundation/run identity before
   separately authorizing deployment and each Glue/Athena reconciliation run.
5. Tear down workloads, verify preserved foundations, perform owner-controlled
   cleanup and review delayed billing. No stage in this sequence was executed here.

The simplified planning estimate is USD 0.408949 gross consumption (rounded USD
0.50 baseline; USD 1.50 reserve), before credits. It is not a spending cap or
permission to run; pricing, eligibility, additional requests/logging and manual
retries require owner review.

## Remaining owner decisions and risks

Read [owner bootstrap](../aws_owner_bootstrap.md),
[runbook](../aws_runbook.md), [IAM matrix](../aws_iam_matrix.md) and
[cost controls](../aws_cost_controls.md) before any account operation.

Owner privileges/current resource presence, Free Plan eligibility, budgets/credits,
Lake Formation/account policies, actual Glue trust propagation, Parquet encryption/
log delivery and real reconciliation remain unverified. Operator job/workgroup/code
updates can affect bounded data and spending; IAM is not a dollar meter or proof of
business-result provenance. Existing old deployment state requires separate migration
review; no state/cloud migration occurred here.
