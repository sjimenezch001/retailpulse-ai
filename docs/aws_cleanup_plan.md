# AWS cleanup proposal: ownership, evidence and separate approval

Prepared offline on 2026-10-11. **No cleanup is authorized or executed.** This is
a review plan, not an executable teardown command. Live ETL/query reconciliation
[passed](aws_live_demo.md); safe operational closeout remains PENDING.

The exact private account/bucket/ARN/version ledger and verified recovery archive
are local and ignored under `artifacts/rp12d/portfolio-closeout-20261011/`.
No credential files, authentication caches or private interview documents are
part of the public package. Do not delete local archives, state, guards, plans,
Gold, frozen models, input seals or historical failure receipts.

## Preservation gate before any proposed destructive execution

The private archive contains 699 original local evidence/recovery files. Every
ZIP member was independently re-read and SHA-256 checked. The corrected runtime
ZIP has a separate byte-verified local copy; the original ZIP remains sealed.
The 125 protected-file baseline, including Gold/frozen evidence and original
video/captions, was checked unchanged. Historical AWS files are hashed in place.

Actual Athena result rows and IDs are saved locally as JSON, along with all
marker values and actual Parquet verification/hash metadata. However, the five
**actual S3 Parquet file bodies**, the **twelve original Athena CSV/metadata
bodies**, and **CloudWatch event messages** are not yet locally exported.
This is an explicit **HOLD**, not a claim that all remote bytes were backed up.

Before deletion, separately authorize preservation-only reads for the current
five Parquet files, two marker bodies and twelve result/metadata objects. Match
each returned VersionId to the recorded ledger; verify known Parquet/marker
hashes, calculate result-file hashes and re-read the local copies. Use existing
permitted current-object reads, ExpectedBucketOwner and bounded sizes; do not
request GetObjectVersion permissions or print credentials. Stop if a current
version changed. Inputs/script bytes and both runtime ZIP versions already have
local byte-identical sources and checksum/version receipts.

The owner should privately preserve useful CloudWatch events via existing
Console access, or explicitly approve their non-retention before log deletion.
The operator's inability to read events is not a reason to broaden IAM.
Archive any additional files with a new manifest, verify them and keep an
additional owner-controlled backup. Archive presence alone is not deletion
approval. Retain backups even after AWS resources disappear.

## Exact recorded ownership

All names below refer only to rp12-demo in sa-east-1 and the approved run
`feadc609ee4301f4e723aa55`. Exact account, ARNs and object VersionIds are in the
private ownership ledger. They are last-observed facts, not a new cloud inventory.

| Resources | Owner / state | Proposed cleanup mechanism |
| --- | --- | --- |
| Athena workgroup `retailpulse-rp12-demo` | Terraform `aws_athena_workgroup.lab`, state serial 20 | Explicit owner decision on service history, described below; preserve state/recovery |
| Glue database `rp_rp12_demo` | Terraform `aws_glue_catalog_database.lab` | Reviewed state-aware saved destroy plan, database after tables |
| Five tables: dim_product, dim_store, mart_sales_daily, pipeline_metadata, store_units | Terraform `aws_glue_catalog_table.lab[...]` | Same saved destroy plan; exactly five table deletes |
| Glue job `retailpulse-rp12-demo` | Direct Boto3, outside Terraform | Explicit exact-name DeleteJob after terminal-run checks; no state import/removal |
| `/retailpulse/rp12-demo/glue/error` and `/retailpulse/rp12-demo/glue/output` | Owner Console, outside Terraform; STANDARD, seven days, five tags | Exact two DeleteLogGroup calls after diagnostics retention decision; no prefix purge |
| Versioned S3 inputs/scripts/curated/results | Boto3 uploads, Glue outputs and Athena outputs; owner-managed dedicated bucket | Separately approved exact key + VersionId list; no recursive bucket or results-prefix purge |
| Dedicated S3 bucket and its security/lifecycle settings | Owner-managed foundation, outside Terraform | Retain through workload cleanup; separate owner deletion only after complete empty verification |
| Glue role, bounded-etl inline and boundary | Owner-managed IAM foundation | Retain through workload cleanup; separate existing-authorized-owner Console review |
| Five attached operator policies | Owner-managed IAM, operator role is a reused identity | Separate lab-permission revocation review; retain existing user/roles/MFA/profiles |

The recorded S3 ledger has **27 versions across 26 keys**: seven original uploads,
one corrected ZIP version, seven curated objects (five Parquet files/two markers)
and twelve Athena CSV/metadata objects. One ZIP version is noncurrent. These
counts exclude unverified later lifecycle changes, multipart uploads or new
objects. A fresh bounded inventory is mandatory; unknown objects/versions are
never added silently to deletion scope.

The approved ExpiresOn tag is 2026-10-17; it does not schedule deletion. If date
guardrails or credentials block a later cleanup, stop for an owner decision
rather than changing the expiration, IAM permissions or approved run.

## Controlled cleanup sequence to review

1. **Fresh read-only gate, separately approved.** Revalidate temporary non-root
   operator identity/account/region, run/source/prepared hashes and state lineage/
   serial/hash against preserved receipts. Confirm five tags and foundation
   security. Read only the exact job, the scoped workgroup/query inventory,
   database/tables and two groups. Require no active job/query or unexpected
   schedule/notebook/named query. Unknown activity stops cleanup; cancellation
   is a separate decision. Enumerate current/noncurrent versions, delete markers
   and multipart uploads only in the dedicated bucket, with ownership and bounded
   pagination. Reconcile every target with the private ledger. AccessDenied is
   NOT proof of absence. Lifecycle-expired known objects require an explicit
   inventory reconciliation, not recreation or an automatic deletion retry.
2. **Untracked workloads.** After the preservation gate, separately approve
   deleting only the Boto3 job and two Console log groups. Match exact names,
   execution role/configuration and tags immediately before each call. Groups
   include their log streams; that data is irreversible without exports. Do not
   import these resources into Terraform or mutate source to make state match.
3. **Athena service-history decision.** Immutable Terraform sets
   `force_destroy=false`. The installed offline AWS API model describes
   `DeleteWorkGroup.RecursiveDeleteOption` as the option for deleting a workgroup
   containing query executions/named queries/notebooks. This workgroup has real
   query history, so a blind seven-resource Terraform destroy is not accepted as
   a complete cleanup procedure. Preserve IDs, results and receipts first.
   The proposed owner-approved exception is an exact `DeleteWorkGroup` with
   `RecursiveDeleteOption=true` for **this workgroup only**, after a fresh inventory
   proves there are no unexpected named queries/notebooks. This deletes AWS-side
   workgroup history; it does not delete S3 results. Do not set force_destroy=true
   or weaken immutable source. No such call is authorized by this plan.
4. **Remaining Terraform resources.** After independently verifying the approved
   workgroup deletion, separately authorize a fresh saved **destroy-mode** plan
   using the already working direct temporary-session authentication and original
   source/provider/state. Archive state/backup first. The provider's ordinary
   authorized refresh should reconcile the absent workgroup without manual state
   edits. Accept **six DELETEs only**: five tables and their database; no CREATE,
   UPDATE, replacement, IAM/bucket or untracked workload action. Preserve refresh
   differences and outputs for review. Apply only that separately reviewed saved
   plan once, then prove workload state/owned resources are absent. A plan showing
   the deleted workgroup still present, unexpected resources or denied reads stops
   the procedure. No stale normal/apply plan or automatic retry is valid.
5. **Versioned S3 data, separate approval.** After all workloads are terminal and
   removed, review the fresh exact key/VersionId deletion manifest. It must cover
   both ZIP versions, all original input/script versions, curated versions/markers
   and all seven known query IDs' results if any exist (six successful IDs plus
   the earlier cancelled ID, whose last recorded output inventory was empty).
   A newly observed cancelled-query file needs provenance/owner review before
   inclusion. Do not create delete markers by omitting VersionId. Existing delete
   markers or multipart UploadIds require their own verified, reviewed targets.
   The existing generic `results/` cleanup predicate is broader than this ledger;
   do not run it blindly. Capture per-item results; stop on any error and record
   any partial cleanup without repeating a failed mutation. Independently verify
   all versions/markers/uploads are empty. Lifecycle expiry is not that proof.
6. **Owner foundations, new manual approval.** Only after verified workload/data
   cleanup may the existing authorized owner delete the dedicated empty bucket,
   bounded-etl inline and exact Glue role, then its unused boundary. Verify no
   unexpected attachments/users of the boundary; otherwise stop. For each
   customer-managed policy deletion, separately review all versions and attached
   entities; remove nondefault versions only after their JSON evidence is saved.
   Retain the existing RetailPulseLabOperator, RetailPulseBootstrap and
   retailpulse-operator user, their MFA/trust, existing profiles and account plan.
   No automatic IAM modification or new administrator access is allowed.
7. **Operator lab-policy retirement, separate owner decision.** Review all five
   operator policies and their versions/other users. If retiring lab permissions,
   stop using operator sessions first, remove the three Allow policies
   (operator-workloads, operator-storage, operator-identity) before removing the
   two Deny guardrail policies. Removing Deny first could leave a temporary
   broader effective permission set. Retire only these exact unused lab policies;
   preserve their historical JSON/versions. No identity or MFA deletion is implied.
8. **Closure evidence and delayed billing.** Independently verify exact resource
   absence, retained local evidence and remaining foundations; record PASS/FAIL/
   NOT VERIFIED separately. Keep USD 5 budget alerts active and review delayed
   gross billing/credits through the owner Console. No account-wide inventory,
   plan upgrade, budget change or promise of a zero final bill is included.

This sequence is a proposal; service-history handling and fresh destroy/data
manifests require owner review before executable commands are prepared. The
unchanged `scripts/aws_lab.py teardown` aggregates deletion/destroy and does not
represent this mixed ownership/history workflow; it also reaches the historical
Athena tag reader using MaxResults=50. Use the established compatible 75-value
reader for future checks, without editing the immutable run or silently ignoring
errors. Do not execute that teardown shortcut for this closeout.

## Separate approval procedure

Approval is not supplied by this document or by the previous Glue/Athena approvals.
The owner should first approve **evidence preservation and scoped read-only
inventory only**. After reviewing that receipt, separately approve the exact
untracked job/two-group deletion and the exact Athena history deletion. Then
review the resulting six-DELETE saved plan before its one apply. Versioned S3
deletion uses its own immutable manifest/hash; owner foundation/IAM cleanup is
a later, separately approved Console procedure. Scope each approval to account,
region, run, resource names, archive hashes and the current inventory.

Every mutation is irreversible or may partially succeed. Preserve guards,
operation IDs, state backups and failure evidence; stop rather than broadening
permissions, changing identity, force-clearing a guard or retrying automatically.
Full account cleanup cannot be claimed until the individual stages and delayed
billing review are evidenced.
