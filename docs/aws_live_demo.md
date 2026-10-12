# Real AWS demonstration with synthetic retail data

Recorded execution: 2026-10-11, sa-east-1. This portfolio laboratory genuinely
ran **S3 → Glue 5.0 Spark → Parquet → Glue Data Catalog → Athena**. Its business
data is synthetic-web-v1, not historical M5, customer sales or model-performance
evidence. The local M5/DuckDB application and frozen models remain separate.

I ran this separate laboratory to exercise the cloud ETL and SQL path against
a small, reproducible synthetic reference. I controlled execution and approvals;
agent-assisted preparation and automated reconciliation supported the procedures.
The temporary infrastructure was removed after execution and evidence preservation,
so the demonstration does not imply continuous hosting.

This document reconciles preserved AWS receipts offline; no additional cloud calls were
made to prepare it. [Machine-readable evidence](evidence/rp12d_live_validation.json)
contains the actual results and IDs. [Acceptance gate](evidence/rp12d_gate.md).

Final closeout update: **2026-10-12**. The demonstration has been torn down;
the [teardown report](aws_teardown_report.md) distinguishes recorded API cleanup
from my reported Console removals, preserves the CloudWatch uncertainty,
and records the pending October invoice. The [final documentation gate](evidence/rp12d_teardown_gate.md)
supersedes the earlier gate's pending closeout status. The execution JSON and
original gate remain unchanged historical evidence.

## Validated results

| Check | Actual result |
| --- | --- |
| Synthetic fact grain | date × store_id × item_id; 252 rows, 252 unique keys |
| Period | 2020-01-01 through 2020-02-11; 42 daily results |
| Total units | 1,386 |
| Store totals | SYN_A 378; SYN_B 462; SYN_C 546 |
| Dimensions | Three stores, two products; 84 joined facts per store |
| Quality | Zero invalid units; seven missing prices; zero invalid null semantics |
| Glue | SUCCEEDED; five actual Parquet datasets and both markers match the immutable reference |
| Athena | Six real SELECTs SUCCEEDED and their complete results equal the prepared references |

`units` is a synthetic reconciliation metric. Missing prices retain explicit
null semantics; no audited revenue or commercial uplift is claimed.

## Genuine execution identifiers and timings

Successful Glue JobRunId:
`jr_2705572727717d01f4a76ff67b5bc9b6540cde7aaaf79695e62ff315b7c62487`.
AWS reported **125 execution seconds and 250 DPUSeconds**. The execution launcher
observed 142.297 seconds including polling; this is a different timing measure.

| Original SELECT | QueryExecutionId | State / comparison | Scanned bytes | Engine ms | Observed query wall seconds |
| --- | --- | --- | ---: | ---: | ---: |
| total_units | e1d3fbf3-dfca-4694-8ff7-7bff5bea1b4f | SUCCEEDED / PASS | 194 | 379 | 2.563 |
| by_store | 88f34e25-15f5-4b73-98ae-1144e467ba9c | SUCCEEDED / PASS | 276 | 444 | 2.515 |
| by_date | 83d4c087-5c7b-4a4c-8d52-2001269f042c | SUCCEEDED / PASS | 492 | 1119 | 2.485 |
| dimension_join | 9d0fcbbf-f41d-40c3-9612-fb39cf44ad73 | SUCCEEDED / PASS | 604 | 865 | 2.469 |
| quality | 952451bf-e434-4516-959c-a5b77317b49e | SUCCEEDED / PASS | 1599 | 1025 | 2.515 |
| row_counts | 7bff21bd-1a3d-47b4-85df-c536aef4b64e | SUCCEEDED / PASS | 0 | 660 | 2.469 |

AWS reported **3,165 scanned bytes** in total. `row_counts` reported zero; the
record is preserved rather than replaced with an estimate. Summed observed
query wall time is 15.016 seconds, excluding the overall foundation/precheck
stage. Billing minimums/rounding mean these bytes are not the billed amount.
There was no result reuse or client resubmission. These observations are not a
production throughput or latency benchmark.

## Lineage and infrastructure ownership

1. The repository's checksum-protected synthetic CSV manifest and four input
   tables form the immutable reference. Independent local SQL supplies expected
   values; actual Athena responses supply observed values.
2. Seven bounded input/script files were uploaded with version IDs and S3-validated
   checksums. A separate approved runtime ZIP correction created another version
   at the same key; the original prepared seal and earlier S3 version were retained.
3. Glue read those inputs and produced `mart_sales_daily`, `dim_store`,
   `dim_product`, `pipeline_metadata` and `store_units` Parquet datasets under the
   current-run `curated/` prefix. Actual Parquet rows, schemas, values and hashes
   were checked against the immutable inputs. `_complete.json` and
   `_metric_candidate.json` independently matched run/provenance/metric references.
4. Five Glue Catalog external tables in `rp_rp12_demo` reference the exact
   curated locations. Workgroup `retailpulse-rp12-demo` ran only the six original
   [SELECT templates](../cloud/aws/sql). Each complete result was reconciled.

The run is `feadc609ee4301f4e723aa55`; local source/bundle/state hashes are retained
in the private recovery archive. Public evidence excludes account numbers,
account-specific bucket URIs, IAM ARNs, credentials, caches and local user paths.

At execution time, seven resources were Terraform-tracked at state serial 20: the Athena workgroup,
Glue database and five tables. The Glue job was created directly with Boto3;
two CloudWatch groups were created manually in Console with STANDARD class,
seven-day retention and five approved tags. The S3/IAM foundations I managed
are outside workload state. The preceding Terraform partial applies and their
recovery state are retained; this is not a fully Terraform-managed deployment.

## Resolved engineering incidents

**Botocore ZIP packaging.** First run
`jr_ad278ffce47b5bcee168c3766b8c75b20be4fbbb673f960eb301d5dd166b496a`
failed with `DataNotFoundError: Unable to load data for: endpoints`.
The original ZIP included boto3/botocore, shadowing Glue's built-in SDK. Its
endpoint JSON existed, but Botocore's filesystem loader could not read it through
zipimport. Offline reproduction confirmed the defect. An independently reviewed
6,250-byte ZIP retained only the five byte-identical application members and
used Glue's built-in dependencies. One separately approved versioned replacement
was followed by the genuine successful run above. No script/job/IAM change or
original-seal rewrite was used; exact live SDK module versions were not captured.

**Athena response representation.** Query
`2ac3b9c6-37d3-4f84-9f46-a953fd400b7d` was cancelled by the first validator after
0.281 seconds while QUEUED, not because the 60-second limit was reached.
Returned SQL omitted the exact final semicolon plus LF and Catalog was
`awsdatacatalog` instead of `AwsDataCatalog`. Strict response comparisons rejected
both. The general sanitizer also hid the long local error category. A separate
reviewed validator accepts only these observed response representations, retains
byte-exact outgoing SQL and strict resource/security checks, and records short
field codes plus all boolean comparisons. Twenty-one offline regression tests
passed before a new guard/contract and separately approved six-query execution
produced the genuine results above. The cancelled receipt and old guard remain.

## Security, cost controls and limits of the proof

The operator uses a non-root temporary assumed-role session with MFA. The Glue
execution role has a bounded inline policy, permissions boundary and reviewed
SourceAccount/SourceArn trust. Private S3 uses SSE-S3, public-access blocking,
ownership enforcement, versioning and lifecycle rules. No real M5/Gold/model
upload, account upgrade or new broad permissions is part of this demonstration.

Glue used two G.1X workers, Glue 5.0 STANDARD, five-minute timeout, zero retries,
concurrency one and a 300-second launcher cancellation deadline. Athena used
engine 3, enforced SSE-S3/expected-owner results, **10,485,760 bytes per query**,
60-second per-query polling, bounded results, zero client retries and exact-ID
cancellation. A durable guard prevented accidental repetition. Internal AWS
service retries and cancellation delays are not a dollar cap.

I confirmed a USD 5 monthly budget with actual-cost alerts at USD 1/3/5,
and previously confirmed USD 120 promotional credits expiring 2027-10-08. Those
are my Console observations, not a fresh billing API audit. Current gross
spend, settled charges and remaining credit after this run are **NOT VERIFIED**.
The October 12 Billing screenshot I described shows an October estimated
payable total of USD 0.00 with Free Plan credits and a Pending invoice. It was
not located locally for this offline review; payable is not gross consumption,
and the final invoice has not been established as closed.
[Earlier regional estimates](aws_cost_controls.md) are dated planning estimates;
no price refresh or billing operation was made during this offline closeout.

The receipts prove account-specific Glue Spark and Athena execution at the
recorded time, not every Free Plan service or future availability. CloudWatch
group configuration was verified; event messages were not API-read because the
operator does not have that permission. Historical operator trust continuity
remains unverified even though current MFA/foundation checks passed.

No `serving/` metric publication, Lambda/API Gateway, Bedrock, Redshift or cloud
forecast evaluation occurred. Current release preparation, MIT licensing and the
independent-verification status are recorded in the
[release checklist](release_checklist.md). Public video hosting and release
publication remain subject to my separate approval.
The [historical cleanup proposal](aws_cleanup_plan.md) retains its original
pre-deletion HOLD. Subsequent approvals, preservation and removals are reconciled
in the [final teardown report](aws_teardown_report.md#ownership-and-teardown-sequence):
the job and six Catalog resources were deleted and read back, all 27 S3 versions
were deleted in one request, and I confirmed foundation removals and
final CloudWatch absence. Operator/bootstrap IAM resources remain intentionally
retained. No additional cleanup or cloud call was performed for this update.
