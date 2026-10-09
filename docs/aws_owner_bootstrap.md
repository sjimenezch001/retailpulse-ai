# Owner-controlled AWS laboratory bootstrap

English canonical guide for RP-12C. Status: **REVIEW CANDIDATE; NOT EXECUTED**.
The owner receives a separate Spanish console walkthrough with exact local resource
names/run JSON. No automatic bootstrap, root automation or permanent access key is provided.

## Review material and identifiers

Run prepare first, then scripts/prepare_aws_bootstrap.py with the approved account,
sa-east-1 and rp12-demo. The local output is artifacts/rp12c/<current-run>/owner-review/.
Use review.json and its checksums to identify the exact proposal. None is installed.

| Foundation | Exact naming contract |
| --- | --- |
| General-purpose bucket | retailpulse-rp12-demo-<account>-sa-east-1 |
| Glue role, path / | retailpulse-rp12-demo-glue |
| Role ARN | arn:aws:iam::<account>:role/retailpulse-rp12-demo-glue |
| Boundary policy, path / | retailpulse-rp12-demo-glue-boundary |
| Boundary ARN | arn:aws:iam::<account>:policy/retailpulse-rp12-demo-glue-boundary |
| Inline execution policy | bounded-etl |
| Existing operator | RetailPulseLabOperator |

Root-path role/policy identifiers intentionally replace the uninstalled RP-12B
path proposal. Console-created roles can use these names without custom IAM paths.
Do not reuse an existing same-name role with different trust/path/permissions.
Missing privileges or name collisions are blockers, not permission to create an
administrator, use root, choose a different bucket or bypass verification.

Required tags: Project=RetailPulseAI, Environment=rp12-demo, Stage=RP12C and the exact
LabId from review.json. ExpiresOn is a separately approved reminder within seven days.
Owner-controlled foundations remain until manual cleanup; tags do not schedule deletion.

## Individually reviewable console steps

Each creation/save/attachment below requires separate owner authorization. This
guide describes later actions; no console operation was performed by RP-12C.

1. Confirm the current non-root console identity, selected account, MFA and existing
   bootstrap permissions. Browser sign-in and operator STS success do not prove owner
   IAM/bucket permissions. Keep Free Plan; stop if any page requests a plan upgrade.
2. Review every JSON, account/region/environment/run and all
   [security limitations](aws_iam_matrix.md). Use an existing eligible budget/credit
   view before any spending. Do not activate Organizations, Control Tower or SSO.
3. In S3, create the exact **general-purpose** bucket in São Paulo. Keep all four
   public-access block flags enabled, ACLs disabled/BucketOwnerEnforced, SSE-S3
   encryption and versioning enabled. Do not upload existing or real data.
4. In bucket Permissions, review then save bucket-policy.json. It only denies
   insecure transport, explicit alternate encryption and SSE-C; it grants no access.
   Review nonpublic status. Do not add public, cross-account or role-session grants.
5. In bucket Management, create the two rules in bucket-settings.json: results/
   current versions expire after one day; all current objects after seven days,
   noncurrent versions after one day and incomplete uploads after one day.
   Confirm the exact scope and review delete markers manually during final cleanup.
6. In IAM Policies, create the customer-managed boundary with the exact name,
   pasting glue-boundary.json. It grants no identity permissions by itself.
   Its explicit denies cap actions/resources and wrong bucket ownership.
   Record the exact ARN; only the owner may change versions or remove this boundary.
7. In IAM Roles, use custom trust and paste glue-trust.json without removing
   SourceAccount/SourceArn conditions. Create the root-path exact role, with no AWS
   managed policies. Set the exact permissions boundary and required tags.
   If the console workflow cannot produce this safely, stop for owner review.
8. Add only the inline bounded-etl policy using glue-execution.json. Do not attach
   AWSGlueServiceRole or other broad AWS-managed policies to solve errors.
   Verify the role has exactly this inline policy, no managed attachments and the
   exact boundary/trust. Role access is only current-run objects and two log streams.
9. Review the five operator documents: operator-storage.json, operator-identity.json,
   operator-workloads.json and every operator-guardrails-*.json. They form one
   mandatory set and are individually below managed-policy size limits.
   In a separately approved step, create custom policies and attach all to the
   existing RetailPulseLabOperator; leave its MFA trust unchanged.
   Do not attach a partial set or combine documents into an oversized inline policy.
10. Review existing operator/session/account resource policies and service eligibility.
    IAM allowlists do not establish live compatibility or spending authority.
    If Glue/Catalog/Athena require a Free Plan change or broader account permissions,
    stop. Lake Formation controls may deny access; do not grant broad lake access.
11. After approval, run STS-only preflight, then the distinct read-only foundation
    check through the [runbook](aws_runbook.md). Verify every security setting and
    exact inline/boundary policy before asking for a saved workload plan.
12. Review the saved plan: one job, database/five tables, workgroup and two groups;
    foundation data references only. Any bucket/IAM/security-configuration/endpoint
    managed change is a blocker. Review fresh expiry, run and infrastructure hashes.
13. Separately authorize deployment of that exact plan, each ETL run, then six-query
    Athena reconciliation. Keep actual identifiers, results and timings local.
    No live PASS is earned by an offline test or an STS response.

## Encryption and role differences

The bucket default ensures SSE-S3 for new writes without encryption headers, including
Spark and temporary paths. The reviewed policy rejects explicit alternate algorithms
and SSE-C; all transport must use TLS. Owner bootstrap starts with an empty bucket.
[S3 encryption behavior](https://docs.aws.amazon.com/AmazonS3/latest/userguide/default-bucket-encryption.html).

No Glue security configuration is created or associated. There is no delegated
regional security-configuration mutation or customer KMS management.
Bookmarks remain disabled, and logs use default service encryption with three-day
retention. SourceAccount and SourceArn protections are retained; real service
propagation remains a compatibility check requiring owner review if it fails.

The operator has no CreateRole, PutRolePolicy, UpdateAssumeRolePolicy, policy-version
mutation, PutBucketPolicy, PutBucketPublicAccessBlock or foundation deletion grants.
PassRole targets exactly this fixed role and only glue.amazonaws.com.
Explicit deny guardrails protect against direct session resource-policy grants;
they must never be omitted.

## Manual foundation cleanup

Only after verified workload teardown and separate owner authorization:

1. Review teardown/recovery evidence and confirm job/query termination, catalog,
   workgroup and log removal. Bucket/role/boundary should still exist.
2. Inspect the exact bucket, including all versions, delete markers and multipart
   uploads. Never use an account-wide purge. Review unexpected/older keys before deletion.
3. Delete only verified remaining lab objects/versions/uploads, then the empty bucket.
4. Delete bounded-etl, then the exact Glue role. Review attachments if unexpected;
   do not remove another workload's role or change trust to enable cleanup.
5. Confirm the exact boundary is unused, then delete its versions/policy manually.
   Operator policies can be detached/deleted only after a separate owner review.
6. Retain state/recovery and local results. Check delayed gross billing, credits,
   remaining resources and logs. Cleanup does not immediately settle the invoice.

## Consumption and readiness

The simplified modeled baseline is approximately USD 0.409 gross for three
five-minute, two-DPU Glue runs and eighteen small Athena queries, plus bounded
storage, requests, catalog and logs. Round planning to USD 0.50 and reserve USD 1.50
within the prior USD 5 target; none is a hard cap or new spending authorization.
Use [cost controls](aws_cost_controls.md) for rates, assumptions and uncertainties.

A passed offline gate can make the candidate ready for separate owner bootstrap
review. It cannot make it ready for live deployment before bootstrap verification,
policy review/attachment, Free Plan/service-access, budget, preflight and plan approval.
