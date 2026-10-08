# RP-12A AWS laboratory runbook

Status on 2026-10-08: implemented and prepared for offline validation. No AWS
identity check, account plan, deployment or cloud workload has been executed.
Use the [gate](evidence/rp12_gate.md) for actual results. The existing
FastAPI/Streamlit application remains independent of this optional lab.

## Scope and data contract

Packaged synthetic inputs -> private S3 -> Glue 5.0 PySpark -> Parquet ->
Glue Data Catalog -> Athena reconciliation -> small metric artifact ->
optional Lambda / IAM-authenticated HTTP API. CloudWatch stores operational logs.

Only the checksum-verified synthetic manifest and four CSVs are uploaded:
mart_sales_daily, dim_store, dim_product and pipeline_metadata. All six packaged
CSV checksums are checked locally; simulated forecasts and metric definitions
are excluded from the upload allowlist. Aggregate input limit: 10 MiB.
Real M5, Gold, frozen models, PBIX, videos and private documents are outside
this flow.

The independent Python and DuckDB references derive 1,386 units, 252 facts,
3 stores and 2 products over 2020-01-01 through 2020-02-11. SYN_A contributes
378 units, SYN_B 462 and SYN_C 546. Facts retain the date/store/item grain,
null price and revenue_proxy values, source version and historical date bounds.
These synthetic observations are not measured forecast performance.

Input checksums plus implementation/SQL identity determine a fixed run_id.
Partial runs overwrite only that run's curated prefixes. A completed rerun
reads and reconciles existing Parquet, including keys and every logical row.
Spark part filenames are not required to be identical. Glue writes a candidate
and completion marker, never the serving artifact. Only six successful,
matching Athena queries publish serving/<run_id>/units.json. A failed query
leaves the endpoint unavailable rather than publishing unreconciled results.
S3 object versioning retains replacements.

## Reproduce the offline checks

Use the existing Python 3.12 environment. AWS dependencies are separately pinned
in [cloud/aws/requirements.txt](../cloud/aws/requirements.txt); they are not added
to the application environment. From the repository root in PowerShell:

~~~powershell
$python = ".venv/Scripts/python.exe"
& $python -m pip install --ignore-installed --target artifacts/rp12/sdk -r cloud/aws/requirements.txt
& $python scripts/install_terraform.py
& $python scripts/aws_lab.py prepare
& $python scripts/aws_lab.py validate
& $python scripts/audit_aws_dependencies.py
& $python scripts/tasks.py verify
& $python scripts/tasks.py security
& $python scripts/tasks.py build
~~~

Use a fresh SDK target when changing pinned versions; do not mix versions in an
existing vendor directory. The installer downloads Terraform 1.15.9 from
[HashiCorp releases](https://releases.hashicorp.com/terraform/1.15.9/) and verifies
the published archive checksum. The signed AWS provider 6.68.0 is pinned in the
committed dependency lock for Windows/Linux AMD64. Downloading development
tools or provider metadata is not an AWS account operation.

prepare produces ignored bundles, trusted input copies, local references and
PyArrow Parquet round trips under artifacts/rp12/prepared/. validate first
checks their freshness, then runs formatting, backend-disabled initialization,
Terraform validation, four explicit mocked plan tests and socket-blocked Python
tests. Any cloud Python/SQL change requires prepare again. The test guard
rejects real providers, apply commands and alternate modules/providers.
Offline validation clears AWS environment configuration, selects empty
credential/config files and disables instance metadata. It uses no account.
[Terraform mocking](https://developer.hashicorp.com/terraform/language/tests/mocking)
does not establish account eligibility or live deployment success.

The local reference uses Python, DuckDB and PyArrow. Native Spark/Glue execution
is NOT RUN on this workstation: Java and PySpark are unavailable. The actual
Glue script uses explicit PySpark schemas, row/key/type/date validations,
aggregation and Parquet readback. Tests of its publication path use stubs and
are labeled accordingly. Glue 5.0 uses Spark 3.5.2/Python 3.11; G.1X with two
workers is selected, with a five-minute timeout, no retries and one concurrent
run. Regional support is documented in the
[Glue 5.0 announcement](https://aws.amazon.com/about-aws/whats-new/2024/12/aws-glue-5-0/)
and [worker reference](https://docs.aws.amazon.com/glue/latest/dg/worker-types.html);
the owner's account access is still unverified.

## Future authorization and authentication prerequisites

Only prepare and validate are authorized in this stage. The commands below
describe a later owner-approved session; do not execute them as part of RP-12A.

The owner must first approve an exact account, sa-east-1 or another explicitly
reviewed region, environment, expiry within seven days, services and gross
spending envelope. Confirm Free Plan service eligibility without accepting an
upgrade or trial. Establish an existing non-root, temporary assumed-role
profile with the selected region configured. Do not create users, access keys,
Organizations or Identity Center infrastructure to satisfy this prerequisite.
Never put credential values in commands, evidence, Terraform variables or Git.

Review [cost controls](aws_cost_controls.md), activate appropriate gross-cost
alerts, confirm subscribers and document the owner's authorization separately.
STS identity alone does not prove service eligibility, price or permission.

Every live operation requires --authorize-live and explicit --profile,
--account, --region and --environment. The runner rejects root/IAM user
identities, account/region mismatches, permanent credentials, ambient credential
overrides, metadata credential sources and custom SDK endpoints. A profile
may legitimately refer to an existing approved temporary-credential mechanism;
review its credential_process/source-profile chain before use. No profile is
created automatically.

| Operation | Behavior and additional controls |
| --- | --- |
| prepare | Offline allowlisting, reference computation and deterministic bundles. |
| validate | Offline Terraform/schema/SQL/security regression checks. |
| preflight | Future explicit STS identity check only; services remain UNVERIFIED. |
| plan | Future real account plan; exact confirmation, budget and service review, expiry required. Saves ignored plan and checksums. |
| deploy | Exact confirmation plus budget/service review; applies only unchanged saved plan, checks ownership, uploads approved files. |
| run-etl | Exact confirmation and budget review; starts one bounded Glue job. |
| query-checks | Exact confirmation and budget review; six allowlisted queries reconcile against local references before publication. |
| endpoint-check | Exact confirmation and budget review; unsigned denial followed by a SigV4-signed request. |
| inventory | Exact state/resource ownership checks, without account-wide scans. |
| teardown | Exact confirmation; stops work, verifies ownership, empties only owned scope, destroys and checks absence. |

The confirmation string is operation:account:region:environment. The PowerShell
wrapper accepts the same arguments. Illustrative future selection (placeholders
must be replaced only after approval):

~~~powershell
$selection = @("--authorize-live", "--profile", "approved-temporary-profile",
  "--account", "<approved-account>", "--region", "sa-east-1",
  "--environment", "rp12-demo")
# Future session only; explicitly approve each operation separately.
& .venv/Scripts/python.exe scripts/aws_lab.py preflight @selection
& .venv/Scripts/python.exe scripts/aws_lab.py plan @selection --budget-reviewed --service-access-reviewed --enable-endpoint --expires-on "<approved-date>" --confirm "plan:<approved-account>:sa-east-1:rp12-demo"
~~~

Then review the saved plan locally before a separately confirmed deploy.
Use matching confirmation strings for each subsequent operation. Do not
substitute a broad terraform apply or run an unreviewed plan. Endpoint defaults
off; --enable-endpoint at planning includes it. Do not change environment/run
identity mid-lab: clean up the old run first. A new code/input identity creates
a different run prefix. Cleanup accepts only the known categories and valid
24-hex run namespaces inside the verified lab bucket, including older run
objects; all other keys stop deletion before any object is removed.

## IAM boundaries and future operator permissions

Terraform creates distinct execution roles. Neither can deploy infrastructure
or pass roles. The Glue role reads approved input/script objects, writes only
its curated/temporary run prefixes and emits logs in pre-created groups.
Lambda reads one exact serving key and writes its own logs. There are no
AdministratorAccess or service FullAccess attachments.

A future owner-approved deployment/operator role is separate and is not
created or attached by this stack. Its policy must cover the following API
operations on the exact resolved inventory, reviewed against the
[AWS service authorization reference](https://docs.aws.amazon.com/service-authorization/latest/reference/reference_policies_actions-resources-contextkeys.html):

| Service | Required operator scope |
| --- | --- |
| S3 | Create/configure/delete the exact lab bucket; get bucket ownership/configuration/tags; list its versions/uploads; read/write/delete only approved input/scripts/curated/results/serving/temporary prefixes. No ListAllMyBuckets or unrelated bucket access. |
| IAM | Create/read/update/delete/tag only the two execution roles in /retailpulse/<environment>/ and their two named inline policies. List attached/inline role policies for provider refresh. No users, keys, admin policy attachments or account security changes. |
| iam:PassRole | Only the exact execution-role ARNs, with iam:PassedToService equal to glue.amazonaws.com or lambda.amazonaws.com. See Terraform output execution_role_pass_permissions. |
| Glue | Create/read/update/delete/tag the exact job and database/five tables; start/get/stop only that job's runs. Catalog reads require the selected account catalog, database and exact table ARNs. |
| Athena | Create/read/update/delete/tag the exact workgroup; start/get/results/stop/list executions restricted to that workgroup. No capacity reservations. |
| Lambda | Create/read/update/delete/tag the exact metric function, manage its single invocation permission and read code signing/concurrency metadata needed by the provider. No function URL or quota changes. |
| API Gateway | Only the selected regional HTTP API and its integration/route/stage/tags; exact execute-api ARN for the signed GET. Review API collection creation permissions separately because its generated ID is not known before creation. |
| Logs | Create/read/tag/delete only the explicit lab log groups and their streams; retention changes only for those groups. |

Wildcard inventory, individually justified: Glue create/get/delete security
configuration APIs have no resource-level ARN support; permit only those three
actions with Resource "*" and aws:RequestedRegion restricted to the chosen
region. Logs DescribeLogGroups similarly requires a regional wildcard; the
runner supplies exact known name prefixes and compares exact names. API
Gateway creation needs the regional /apis collection, then a generated API-ID
wildcard for the initial create transaction; narrow subsequent access to the
saved API ID and lab tags wherever supported. STS GetCallerIdentity has no
resource-specific permission scope. Verify current per-action support before
granting a future profile; do not solve AccessDenied with service-wide FullAccess.

Execution-role wildcards are limited to objects inside four exact run prefixes
and streams inside exact log groups. S3 ListBucket uses StringLikeIfExists:
prefix-bearing listings must match those prefixes; prefix-less bucket metadata
probes can succeed on this one lab bucket. This also permits a prefix-less list
of names in that bucket, never object reads outside the allowed prefixes.
[HeadBucket requires ListBucket](https://docs.aws.amazon.com/AmazonS3/latest/API/API_HeadBucket.html).
The TLS bucket policy uses Principal "*" and s3:* only in a DENY statement, not
as a permission grant. Glue trust additionally requires the selected SourceAccount and regional
Glue SourceArn. These conditions are retained; service propagation of this
context remains a live compatibility check. Do not silently remove them if
role assumption fails. The caller's exact PassRole policy and execution
policies provide additional resource boundaries. No KMS key, VPC, NAT, EC2 or remote state infrastructure is created.

## Live acceptance to perform later

Record actual Glue job ID/state/runtime, actual Athena IDs/scanned bytes/times,
six matching query results and the publication receipt. Keep generated cloud
identifiers and state in ignored local evidence. The client rejects arbitrary
SQL, S3 keys and database names. Polling and result retrieval are bounded; it
cancels a query after its deadline and rejects paginated oversized results.
A stable query token reuses a prior execution for the same run/query; after
the one-day result lifecycle, a new authorized run identity is needed rather
than silently replaying charges.

GET /metrics/units?store=SYN_A must reject unsigned requests and return a
SigV4-authenticated response with mode synthetic, metric/unit units, value 378,
period, version, run and manifest provenance. Lambda reads a bounded artifact,
not Athena per request. It rejects unknown/duplicate arguments and returns safe
errors for unavailable, stale or unreconciled artifacts. The endpoint is
Internet-addressable with AWS_IAM authentication, not a private VPC endpoint.
Its five-second/128-MiB Lambda and 1 request/second, burst 2 API throttles bound
normal use; no reserved/provisioned concurrency or quota change is requested.
[HTTP API IAM authorization](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-access-control-iam.html)
requires SigV4 and an authorized invoke identity.

These are future acceptance conditions, not completed measurements.

## Shutdown, cleanup and recovery

Keep the original source checkout, prepared bundle, local variables, reviewed
plan, state and inventory together until cleanup succeeds. State lives under
artifacts/rp12/live/<lab_id>/; do not commit it. An expiry tag is only a reminder.

The separately authorized teardown validates account/region, state resource IDs,
Terraform outputs, service tags, database/table provenance and exact locations.
It backs up recovery state, stops active runs/queries and waits for termination.
Only then does it enumerate and remove this lab's object versions, delete
markers and incomplete uploads. Unknown prefixes, ownership mismatches, denied
access or inventory limits stop cleanup. No arbitrary bucket purge is available.

Terraform removes the known resources and explicit logs. The runner checks empty
state and exact resource absence; AccessDenied or ambiguous errors are not proof
of deletion. It retains recovery copies even on success. Review any unverified
items and billing/log retention after cleanup; asynchronous billing can lag.

A partial apply, manually removed resource, >100 Glue runs, >50 query IDs,
>2,000 object versions or >100 multipart uploads can require manual recovery.
Do not bypass the guards or delete state: use the saved state/plan/inventory to
review the exact resource ARNs with the owner, obtain separate permission for
the remaining cleanup and reconcile state only after ownership and deletion
are verified. Never run account-wide cleanup or infer ownership from a prefix.
Transient permission/service errors remain blockers for live cleanup.

## Service learning evidence

| Service | Implemented evidence | What remains unproven |
| --- | --- | --- |
| S3/IAM | Private/encrypted/TLS-only storage, role separation, ownership and prefix checks. | Actual account policies, API permissions and lifecycle behavior. |
| Glue | Genuine bounded PySpark ETL, explicit schemas and repeatable logical publication. | Native Spark and AWS job execution. |
| Catalog/Athena | Five explicit tables, six independently checked SQL queries, workgroup controls. | Actual scan volume, latency and execution receipts. |
| Lambda/API Gateway | Artifact-backed handler, IAM route and signed smoke client with offline tests. | Real unsigned denial and signed success. |
| CloudWatch | Explicit groups, three-day retention, safe API log fields. | Actual service log delivery and volume. |

This tiny synthetic lab demonstrates implementation decisions and offline
reasoning. It does not establish production experience or measured scalability.
