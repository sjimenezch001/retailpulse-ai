# Redshift extension — disabled, access unverified

RP-12A contains no Redshift Terraform resources, subscriptions, trials, network
infrastructure or executions. The owner's generic activation/Free Plan redirect
does not establish eligibility. The S3/Glue/Athena lab is independent of Redshift.

A later, separately authorized extension could use the same synthetic Parquet,
with explicit fact/date/store/item grain and store/product dimensions. Keep
source column order and types aligned with the
[catalog schemas](../infra/aws/catalog.tf.json); preserve null prices and
revenue_proxy. Load into staging tables from an exact, owner-reviewed S3
manifest with mandatory objects/content lengths, then validate before replacing
a published synthetic schema in one transaction. Do not append duplicates or
load real Gold. [COPY Parquet and manifest examples](https://docs.aws.amazon.com/redshift/latest/dg/r_COPY_command_examples.html)
describe the supported load mechanism; IAM must read only that run's input.

Reconcile total units, per-store/per-date sums, row counts, uniqueness, nulls
and joins with the existing [allowlisted SQL](../cloud/aws/sql/) and independent
DuckDB reference. Expected values remain 1,386 total units, 378 for SYN_A and
252 facts over 2020-01-01 through 2020-02-11, derived anew from the manifest.
A successful COPY alone is not validation. Record actual query IDs, durations
and consumption only after execution.

Before proposing infrastructure, verify Free Plan eligibility, sa-east-1
availability, regional pricing, existing approved network access, permissions
and the smallest supported Serverless base/max capacity. Do not inherit the
documented default 128 RPUs or assume 4 RPUs is available in Sao Paulo: that
region is absent from the current
[4-RPU capacity list](https://docs.aws.amazon.com/redshift/latest/mgmt/serverless-capacity.html).
Set an explicit maximum capacity and a small daily RPU-hour limit with the
[deactivate/turn-off-queries action](https://docs.aws.amazon.com/redshift/latest/mgmt/serverless-workgroup-max-rpu.html),
plus a short statement timeout and separately reviewed gross-cost estimate.
Usage limits do not remove storage or replace cleanup. No capacity or dollar
estimate for Redshift is included in the core lab's $5 target.

After a later test, cancel active queries; inventory the exact workgroup,
namespace, schemas, IAM roles/policies, logs, snapshots/recovery points, S3
staging objects and any explicitly authorized network resources. Verify
ownership before deletion, retain recovery information, remove only that
extension and confirm no billed leftovers. No account-wide cleanup or network
provisioning is authorized now. If access remains blocked, leave this extension
disabled and keep the core lab unchanged.
