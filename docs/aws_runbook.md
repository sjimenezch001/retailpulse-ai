# AWS laboratory runbook

RP-12C candidate, reviewed locally on 2026-10-08. AWS live acceptance is **PENDING**.
The workload is S3 → Glue 5.0 ETL → Glue Data Catalog → Athena, with two explicit
CloudWatch log groups. Lambda, API Gateway and Redshift are deferred.
The local FastAPI/Streamlit application and frozen model artifacts are independent.

## Ownership and authorization

The owner manually creates and controls one private SSE-S3 bucket, its security
settings, one fixed-trust Glue execution role, its exact inline execution policy,
and an immutable permissions boundary. Terraform reads these foundations; it never
creates, edits, imports or destroys them. See the
[owner bootstrap guide](aws_owner_bootstrap.md) and [IAM matrix](aws_iam_matrix.md).

Terraform manages only one Glue job, one catalog database/five tables, one Athena
workgroup and two log groups. The operator cannot create or mutate IAM roles/policies
or bucket security settings. PassRole is limited to the exact owner Glue role and
glue.amazonaws.com. All operator policies and deny guardrail shards are mandatory.

No owner bootstrap, policy attachment, login/refresh, account discovery, workload
or live plan is authorized by this offline stage. Non-root temporary assumed-role
credentials, explicit profile/account/region/environment and operation confirmation
remain required. Existing MFA trust is unchanged. STS success alone establishes
neither service eligibility nor a spending authorization.

## Offline preparation and verification

Use the existing pinned application environment and isolated cloud SDK; dependency
versions, package version and the Terraform/provider lock remain unchanged.

~~~powershell
& .venv/Scripts/python.exe scripts/aws_lab.py prepare
& .venv/Scripts/python.exe scripts/aws_lab.py validate
& .venv/Scripts/python.exe scripts/prepare_aws_bootstrap.py --account "<approved-account>" --region sa-east-1 --environment rp12-demo
~~~

Prepare authenticates the packaged synthetic CSVs locally, builds the Glue bundle,
round-trips local Parquet and independently computes six reference queries.
It never reads real Gold for upload. Run identity includes cloud code, SQL,
dependency pins and current infrastructure definitions. Any change requires a fresh
prepare and owner policy review; stale prepared files are rejected.

The review generator writes exact-account/run JSON under
artifacts/rp12c/<run_id>/owner-review/. Nothing is installed. The RP-12B bundle remains
unchanged historical evidence and must not be used for the new run.
No fresh Lambda deployment bundle is built; old ignored files are not authorized inputs.

Validate uses empty AWS configuration, metadata disabled, backend-disabled init and
only explicitly mocked Terraform plan tests. Python cloud tests forbid real sockets
and credential discovery. Do not substitute a live Terraform plan for these tests.
An optional offline policy checker consumes previously downloaded public AWS service
authorization metadata; it performs no network or account request itself.

## Foundation verification and transport/encryption

The runner verifies the exact owner/region/tags, all four public-access blocks,
BucketOwnerEnforced ownership, AES256 bucket default, versioning, exact retention
rules, deny-only TLS/encryption policy and nonpublic policy status. It checks the
Glue role ARN/root path, fixed trust, exact boundary/default policy version, one
named inline policy, and absence of managed policy attachments. Missing, denied,
different or stale metadata fails closed before planning, uploading or running ETL.

Terraform data sources additionally check exact identifiers, role trust/boundary/tags
and verified bucket-policy/boundary hashes. Data references are not managed resources.
Use the runner: Terraform's S3 data source alone does not verify every security setting.

The Glue security configuration and job security_configuration property are omitted.
The entire input/scripts/curated/temporary/results/serving namespace uses the one
verified bucket default; alternate explicit SSE-KMS and SSE-C writes are denied.
Absent encryption headers are allowed so Spark/multipart uploads inherit AES256.
Runner JSON/CSV uploads explicitly request AES256; Athena enforces SSE_S3 results.

[S3 default encryption](https://docs.aws.amazon.com/AmazonS3/latest/userguide/default-bucket-encryption.html)
covers new uploads with absent headers. This does not retroactively encrypt older
objects. The owner must bootstrap an empty dedicated bucket; existing objects or
unexpected runs require review. TLS remains enforced by the reviewed bucket policy.
This differs from a Glue security configuration: no customer KMS encryption for logs
or bookmarks is configured. Bookmarks are disabled; log groups have default service
encryption and three-day retention. No KMS administration is delegated.
[AWS Glue security configuration](https://docs.aws.amazon.com/glue/latest/dg/encryption-security-configuration.html).

The existing Glue SourceAccount and regional Glue SourceArn trust conditions remain.
Real service-context propagation, native Spark, S3 publication and log delivery are
unverified; stop for owner review if incompatible, without removing trust conditions.

## Later owner-approved acceptance sequence

1. Review owner bootstrap JSON and the exact current run.
2. Separately authorize manual bucket/role/boundary setup.
3. Review all operator policy shards and potential resource-policy grants; only
   after approval may the owner attach them to the existing operator role.
4. Check Free Plan eligibility, regional service access and any existing
   Lake Formation/catalog controls; do not create Organizations, Identity Center,
   Control Tower, upgrade the plan or add broad permissions to resolve denials.
5. Review gross consumption, credits/expiry and existing budget/notification coverage.
6. Authorize STS-only preflight, then the distinct read-only foundation check.
7. Authorize a saved plan; inspect only workload resources and read-only foundations.
8. Authorize deployment of that exact reviewed plan.
9. Authorize each Glue run and six-query Athena reconciliation separately.
10. Authorize workload teardown, verify foundations survive, then separately review
    manual foundation cleanup and delayed billing.

[Cost controls](aws_cost_controls.md) are planning estimates and guards, not a hard
billing cap. All live steps remain PENDING until actual receipts exist.

~~~powershell
$selection = @("--profile", "<temporary-role-profile>", "--account", "<approved-account>", "--region", "sa-east-1", "--environment", "rp12-demo", "--authorize-live")
# Future separately approved commands only; not executed by this stage.
& .venv/Scripts/python.exe scripts/aws_lab.py preflight @selection
& .venv/Scripts/python.exe scripts/aws_lab.py foundation-check @selection
& .venv/Scripts/python.exe scripts/aws_lab.py plan @selection --budget-reviewed --service-access-reviewed --expires-on "<approved-date>" --confirm "plan:<approved-account>:sa-east-1:rp12-demo"
~~~

Deploy/run-etl/query-checks/teardown use their matching confirmation strings.
No endpoint flag is allowed; --enable-endpoint and endpoint-check fail before
authentication. Expiry must be within seven days; a tag does not delete resources.

## Data and reconciliation contract

Only the authenticated synthetic-web-v1 CSV manifest/four tables are uploaded:
55,218 bytes, 252 facts, three stores, two products and six store/item series.
References remain 1,386 units: SYN_A 378, SYN_B 462, SYN_C 546, 2020-01-01 through
2020-02-11. Forecast observations and real M5 are excluded.

Glue uses two G.1X workers, five-minute timeout, MaxRetries=0, MaxConcurrentRuns=1,
no queue, autoscaling, crawler or schedule. ETL verifies schemas, keys, row/aggregate
counts, logical Parquet readback and completed-run consistency. Native Spark and
AWS execution must be verified later; local stubs are not those results.

Athena has one enforced engine-v3 workgroup, expected bucket owner, SSE_S3 results
and a 10,485,760-byte scan cutoff. Six fixed SQL queries have bounded polling/results,
with cancellation on timeout. Only successful real reconciliation can publish the
serving metric. Retaining that artifact does not enable a Lambda/API workload.

## Shutdown, cleanup and recovery

Use only the separately confirmed teardown command. It validates local state,
inventory, service ownership and owner foundations, preserves recovery state, stops
owned jobs/queries, and removes only current-run object versions/delete markers and
multipart uploads plus results/. Unknown keys, older run IDs, denied reads or inventory
limits stop deletion before the first destructive object call.

Terraform destroy then removes only workload resources. The runner verifies exact
job/database/workgroup/log absence and separately re-verifies that the owner bucket,
role and boundary still exist unchanged. A successful workload report records owner
cleanup PENDING; it is not evidence of account-wide cleanup.

A legacy state containing managed bucket, IAM, security-configuration or endpoint
resources is rejected before planning or destroying. Never let a changed stack
silently delete RP-12A foundations. If any old deployment exists, preserve state,
obtain separate owner migration review and reconcile its lifecycle manually.
No state removal/import or cloud migration was performed here.

After complete workload teardown, the owner separately reviews all remaining
versions/uploads and deletes the empty dedicated bucket, execution inline policy,
role and unused boundary. The operator has no foundation deletion permissions.
Keep all recovery evidence until these deletions and billing are verified.
See the [manual cleanup checklist](aws_owner_bootstrap.md#manual-foundation-cleanup).

## Remaining acceptance evidence

Record genuine Glue run IDs/state/runtime, six Athena execution IDs/scanned bytes/
latencies and reconciled results, actual logging and cleanup receipts. Live acceptance
is PENDING. IAM static checks do not evaluate actual SCPs/RCPs, account resource
policies, service availability, propagation or Free Plan restrictions.
