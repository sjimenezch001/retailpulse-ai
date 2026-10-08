# AWS laboratory cost controls

Review date: 2026-10-08. Proposed region: sa-east-1. No cloud spending is
authorized in RP-12A. The later first-experiment target is **USD 5 of gross
service consumption before promotional credits**, not a hard billing cap.

The owner supplied a Free Plan screenshot showing USD 100 credit and 183 days
remaining at that time. These are historical owner observations, not API
verification. S3, Glue, Athena and IAM availability remain unverified. STS
success would not establish eligibility. Redshift's activation/Free Plan
redirect leaves its access unknown; no upgrade or trial is authorized.

## Regional planning estimate

Rates below were read from the official regional AWS Price List offers on the
review date. They exclude credits and do not assume free-tier benefits. The
local raw pricing responses are ignored evidence under artifacts/rp12/.
Recheck the linked prices and account eligibility before any later spending.

| Component | Regional unit price | Conservative first experiment assumption | Estimated USD |
| --- | --- | --- | ---: |
| Glue 5.0 STANDARD ETL | $0.69/DPU-hour | 3 separately approved runs x 2 G.1X DPUs x 5 minutes | 0.345000 |
| S3 Standard | $0.0405/GB-month; $0.007/1,000 PUT/COPY/POST/LIST; $0.0056/10,000 GET/other requests | 0.1 GB for 7 days; 2,000 requests of each class | 0.016065 |
| Glue Catalog | $1/100,000 object-months; $1/million requests | 6 objects for a full month; 1,000 requests; no free allowance deducted | 0.001060 |
| Athena | $9/TB scanned | 18 queries billed at a 10 MB minimum each | 0.001620 |
| Lambda x86 | $0.0000166667/GB-second; $0.20/million requests | 100 requests x 128 MiB x 5 seconds | 0.001062 |
| HTTP API | $1.59/million requests | 100 requests | 0.000159 |
| CloudWatch Logs | $0.90/GB ingest; $0.0408/GB-month storage | 0.05 GB ingested and retained 3 days | 0.045204 |
| Total modeled consumption | Before promotional credits | Rounded planning baseline | **0.410170** |

Official regional sources:
[Glue](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AWSGlue/current/sa-east-1/index.json),
[S3](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonS3/current/sa-east-1/index.json),
[Athena](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonAthena/current/sa-east-1/index.json),
[Lambda](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AWSLambda/current/sa-east-1/index.json),
[API Gateway](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonApiGateway/current/sa-east-1/index.json),
[CloudWatch](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonCloudWatch/current/sa-east-1/index.json).
Athena's query billing minimum is described in
[Athena pricing](https://aws.amazon.com/athena/pricing/).

Round the baseline up to $0.50 and reserve **$1.50** for a later approved
experiment, within the owner's $5 planning target. This is an estimate, not a
quote or consumption limit. Driver startup/billing details, request rounding,
metadata calls, extra logs, transfers, taxes, price changes and retries initiated
by a person create uncertainty. Budget administration/notifications and any
existing account usage must also be reviewed. No $100 credit offset is deducted.
This lab makes no measured runtime or live cost claim.

## Enforced controls and limits

One selected account/region/environment; no region scans. Input <=10 MiB,
10,000 rows, bounded schemas and no real business data uploads. Glue uses two
G.1X workers, timeout 5 minutes, MaxRetries=0, MaxConcurrentRuns=1 and no queue,
schedule, crawler, autoscaling or interactive session. An operator still must
approve each run; repeated manual invocations are not limited by a dollar meter.

Athena uses one enforced engine-v3 workgroup with SSE-S3 results, expected
bucket owner and a 10,485,760-byte per-query scan cutoff. This is the minimum
accepted by the pinned provider. There are no capacity reservations. Six
allowlisted queries per check have a 60-second logical polling deadline,
bounded SDK timeouts, cancellation and at most one 1,000-row result page.
Network time can extend wall-clock polling beyond that logical deadline.
A cancelled or failed query can still incur charges and leave partial outputs;
the [workgroup limits documentation](https://docs.aws.amazon.com/athena/latest/ug/workgroups-setting-control-limits-cloudwatch.html)
explains why a scan threshold is not an account billing cap.

The endpoint reads one <=64-KiB artifact. Lambda is 128 MiB / 5 seconds; API
throttling is 1 request/second with burst 2. Throttling is best effort and is not
a monthly request/spend cap. No provisioned/reserved concurrency is configured.
Logs retain three days. S3 results expire after one day, all lab objects after
seven, noncurrent versions after one day and incomplete multipart uploads after
one day. Deletion is asynchronous; delete markers and surviving resources still
require the teardown checks. IAM/global service metadata and same-region data
transfer assumptions must be revisited if the design changes.

Project, Environment, LabId, Stage and ExpiresOn tags are set where supported.
Catalog parameters also record run/lab provenance. ExpiresOn does not schedule
deletion. Cost allocation tags may need owner activation and can have reporting
delay; they are not the only safety control.

## Owner budget setup before the first live run

No budget, subscriber, billing permission or account setting is created by this
repository. In a separately approved session the owner should:

1. Review an existing budget or create a COST budget in USD covering this
   experiment's dates, with a $5 limit and actual alerts at $1, $3 and $5.
   Add a forecast alert where eligible. Review any budget/notification charges.
2. Track unblended gross consumption, with IncludeCredit=false,
   IncludeRefund=false and IncludeDiscount=false; explicitly review tax/support
   treatment. The [CostTypes reference](https://docs.aws.amazon.com/aws-cost-management/latest/APIReference/API_budgets_CostTypes.html)
   shows these offsets otherwise default to included.
3. Use account-wide monitoring as a backstop while tags become available;
   optionally add the exact regional/project filter after verifying cost-tag
   activation. Confirm authorized recipients actually receive notifications.
   Do not put private emails in tracked Terraform examples.
4. Verify the budget's displayed cost basis against billing before running
   workloads. Existing account costs and reporting delay can affect alarms.
5. Check consumed gross cost after each run and perform the
   [shutdown/teardown checklist](aws_runbook.md#shutdown-cleanup-and-recovery).
   Retain state until deletion is verified.

Budget notifications are delayed warnings, not immediate cutoffs. No automated
budget action, account plan change or spending authorization is implied.
