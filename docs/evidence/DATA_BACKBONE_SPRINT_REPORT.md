# Data Backbone Sprint Report — real M5 validation

Date: 2026-10-07 (America/Sao_Paulo). Branch: `feat/data-backbone`.
Implementation baseline: `0fac514`. Existing Python 3.12.10 `.venv` reused.

## Gate outcome

**REAL M5 DETECTED: YES.** RP-02, RP-03, RP-04, RP-05 and RP-06: **PASS —
REAL-DATA VALIDATED**. This supersedes the initial synthetic-only pending
status for the measured pilot. All original implementation commits are preserved.

Real inputs were structurally scanned before execution; hashes were checked
again after profiling. No schema failure or pipeline defect was exposed.
Source code, SQL, test fixtures, dependency versions and package structure are
unchanged. No defect was hidden or test weakened. No implementation fix commit
was necessary. Configuration and the sample were derived solely from real M5.

## Real sources

| Filename | Bytes | Rows | Columns |
| --- | ---: | ---: | ---: |
| calendar.csv | 103,469 | 1,969 | 14 |
| sell_prices.csv | 203,395,785 | 6,841,121 | 4 |
| sales_train_evaluation.csv | 121,736,518 | 30,490 | 1947 |

SHA-256, independently reproduced:

- `calendar.csv`: `d12b5914ef03e66649adf5dd9e996e6602251c22b7a6af8f1f7e3aa12f8860f5`
- `sell_prices.csv`: `9da3ad1f8b8ccacdbdc70612191dd375ec24a4ac6625c24b75b3bc60b0bed2ef`
- `sales_train_evaluation.csv`: `4b4a47c44c38380d2a9168216fea8c9ff2f31b1ddb772f8a0995952a038b8aa0`

Calendar: `d` and date keys, retail week, weekday/month/year, event names/types
and SNAP indicators; dates 2011-01-29–2016-06-19. Sales: six identifier fields
plus int64 `d_1`–`d_1941`; observed dates 2011-01-29–2016-05-22. Prices:
store/item/retail-week key and double sell_price. The source spans 10 stores,
7 departments, 3 categories, 3 states and 3,049 items.

No source duplicate rows or required-field schema problems were found. Sales
and prices have no null cells. Calendar's absent events account for 1,807 nulls
in each first-event name/type field and 1,964 in each second-event field.
Full-column cardinalities/null counts are in the real raw manifest. Source
unit bounds are 0–763 with no null or non-integer daily columns.

Full-source weekly price coverage over observed sales dates is 6,719,161 /
8,476,220 keys (**79.270724%**). Future calendar weeks are excluded.

## Derived pilot and sample

Stores: **CA_1, CA_2, CA_3**. Departments: **FOODS_1, FOODS_2**. The unchanged
selection rule chooses the first three sorted stores and first two sorted
common departments. The pilot has **614 items, 1,842 item/store series and
1,941 observed dates**. No arbitrary IDs were inserted into the implementation.

The genuine sample has six rows, one first item per store/department, and is
36,243 bytes. Every field was matched exactly to the source CSV via a streaming
comparison. Provenance includes the actual sales source SHA-256. Full raw and
generated datasets and the real row-level sample remain Git-ignored and local.
Only the sample selection rule and source-checksum provenance metadata are
versioned; the repository does not distribute real M5 observations.

## Pipeline outputs, lineage and reconciliation

| Layer / entity | Actual rows |
| --- | ---: |
| Bronze calendar | 1,969 |
| Bronze prices | 6,841,121 |
| Bronze wide sales | 30,490 |
| Silver fact_sales_daily | 3,575,322 |
| Silver dim_calendar | 1,969 |
| Silver dim_product | 614 |
| Silver dim_store | 3 |
| Gold mart_sales_daily | 3,575,322 |
| Gold mart_store_weekly | 1,668 |
| Gold mart_demand_alerts | 380,925 |
| Gold fact_forecast after RP-06 | 464,184 |
| Gold forecast_evaluation | 222 |

**4,530,250 units** reconcile independently from selected wide Bronze to Silver,
daily Gold and weekly Gold. The daily row count equals 1,842 × 1,941.
Bronze's source-level input and output counts all reconcile. Two Bronze runs
used the same run ID, hashes, counts and original timestamp; the rerun reused
the snapshot without duplication.

- Bronze run: `47b8b962c868f3c60fc8`.
- Silver run: `3bb14677a2a3a1205013`.
- Gold run / forecast source: `20f4dae75fff8e79204e`.
- Source ingestion: `2026-10-07T21:29:04.505820+00:00`.
- Gold generation: `2026-10-07T21:33:38.610052+00:00`.
- Paths: `data/processed/bronze/runs/<run_id>/`,
  `data/processed/silver/runs/<run_id>/`, `data/processed/gold/retailpulse.duckdb`.

Bronze metadata was grouped across every row to verify source filename,
source checksum, run ID and timestamp; output SHA-256 hashes were recomputed.
Independent Silver audits found zero duplicate grain keys, invalid units,
calendar/product/store mapping failures, price-join mismatches or wrong lineage.
Per-series wide/long values were also checked at five observed day offsets.
Dates are typed; pilot unit bounds are 0–157.

## Missing prices and metric findings

Silver and Gold retain **977,382 missing-price rows (27.336894%)** with explicit
flags. Every one has zero observed units, but that does not establish inventory
availability or stockouts. No sales rows were silently dropped.

Under the existing conservative rule, **1,383 of 1,668 weekly rows have NULL
canonical revenue_proxy**. The known-price partial sum is approximately
13,500,903.56; it is not audited revenue or an asserted complete accounting total.
The documented noncausal spike heuristic flags 380,925 daily rows.

Every daily revenue multiplication and price-change calculation was checked.
Independent calendar RANGE windows reproduced the 7/28-day rolling means;
these exclude today and all future dates. The spike rule was independently
recomputed. All metric mismatch counts were zero; daily and weekly keys are
unique. The SQL quality query returned no failures. Definitions did not change.

Freshness is **3,790 days** from actual final sales date 2016-05-22 to explicit
as_of 2026-10-07. New pipeline execution does not make historical sales current.

## Real baseline results

| Phase | Training dates | Holdout / target dates |
| --- | --- | --- |
| Validation | 2011-01-29–2016-03-27 | 2016-03-28–2016-04-24 |
| Test | 2011-01-29–2016-04-24 | 2016-04-25–2016-05-22 |
| Future | 2011-01-29–2016-05-22 | 2016-05-23–2016-06-19 |

There are 51,576 observations per model and holdout. WMAPE below is percentage
display; machine-readable evidence stores its ratio. MAE/RMSE are item/store
daily units. No random split, test-based tuning or within-horizon updating occurs.

| Split | Model | WMAPE | MAE | RMSE |
| --- | --- | ---: | ---: | ---: |
| test | last_value | 105.934365% | 1.795622 | 3.014355 |
| test | rolling_mean | 79.482353% | 1.347252 | 2.361194 |
| test | seasonal_naive_7 | 93.280944% | 1.581142 | 2.789959 |
| validation | last_value | 105.247167% | 1.618602 | 2.915572 |
| validation | rolling_mean | 83.774019% | 1.288365 | 2.190055 |
| validation | seasonal_naive_7 | 100.186588% | 1.540775 | 2.873446 |

Rolling mean has the lowest measured errors among these three models on both
holdouts. This is a pilot comparison, not a production-quality or generalization
claim. WMAPE may exceed 100%; it is not a bounded accuracy score.

Test segmentation by store and department:

| Segment type | Segment | Model | WMAPE | MAE | RMSE |
| --- | --- | --- | ---: | ---: | ---: |
| department | FOODS_1 | last_value | 98.6265% | 2.034171 | 3.580348 |
| department | FOODS_2 | last_value | 111.4038% | 1.666158 | 2.657185 |
| store | CA_1 | last_value | 110.2762% | 1.592950 | 2.663390 |
| store | CA_2 | last_value | 106.2886% | 1.860051 | 3.035983 |
| store | CA_3 | last_value | 102.2890% | 1.933865 | 3.308802 |
| department | FOODS_1 | rolling_mean | 81.8235% | 1.687610 | 3.077258 |
| department | FOODS_2 | rolling_mean | 77.7302% | 1.162535 | 1.860581 |
| store | CA_1 | rolling_mean | 84.2486% | 1.216978 | 2.079436 |
| store | CA_2 | rolling_mean | 78.9898% | 1.382321 | 2.351195 |
| store | CA_3 | rolling_mean | 76.2967% | 1.442457 | 2.621743 |
| department | FOODS_1 | seasonal_naive_7 | 95.5962% | 1.971671 | 3.532618 |
| department | FOODS_2 | seasonal_naive_7 | 91.5482% | 1.369197 | 2.288133 |
| store | CA_1 | seasonal_naive_7 | 97.7289% | 1.411703 | 2.471475 |
| store | CA_2 | seasonal_naive_7 | 92.4550% | 1.617962 | 2.794601 |
| store | CA_3 | seasonal_naive_7 | 90.6470% | 1.713762 | 3.071422 |

Representative test horizons:

| Horizon | Model | WMAPE | MAE | RMSE |
| --- | --- | ---: | ---: | ---: |
| 1 | last_value | 112.6399% | 1.693268 | 3.159272 |
| 14 | last_value | 98.3631% | 1.826819 | 2.957810 |
| 28 | last_value | 85.4334% | 1.910423 | 3.168366 |
| 7 | last_value | 79.9296% | 1.725299 | 2.836094 |
| 1 | rolling_mean | 79.2241% | 1.190942 | 2.504086 |
| 14 | rolling_mean | 78.4148% | 1.456336 | 2.427723 |
| 28 | rolling_mean | 71.0991% | 1.589887 | 2.805868 |
| 7 | rolling_mean | 68.1482% | 1.470994 | 2.583162 |
| 1 | seasonal_naive_7 | 98.9166% | 1.486971 | 2.941430 |
| 14 | seasonal_naive_7 | 98.3631% | 1.826819 | 2.957810 |
| 28 | seasonal_naive_7 | 85.4334% | 1.910423 | 3.168366 |
| 7 | seasonal_naive_7 | 79.9296% | 1.725299 | 2.836094 |

[All 222 segmented metric rows](real_m5_baseline_metrics.csv) include both
holdouts, all stores/departments, demand levels and every horizon from 1 to 28.
Future forecasts have NULL actuals; no future error numbers are claimed.

Independent SQL verified all forecast values using only observations at or
before the recorded origins, plus actuals, source lineage, temporal bounds and
overall metrics. There were zero mismatches. The exact baseline rerun produced
**zero changed rows** across all 464,184 forecasts and 222 evaluations, using
bidirectional `EXCEPT ALL`. Execution timestamps may refresh; predictions do not.

No real aggregate segment had a zero WMAPE denominator. A diagnostic slice of
100 real zero-actual test rows explicitly returned WMAPE=NULL and the zero flag;
this is a contract check, not a business segment. Synthetic tests also cover it.

## Business-query execution

All five CLI queries ran. Before RP-06, forecast errors returned zero rows;
afterward the same query returned **168 model/split/horizon rows**.

- Sales trend: 1,941 rows. On 2016-05-22, units=4,119, revenue_proxy≈13,012.34,
  missing_price_rows=0. On 2011-01-29, units=2,557, revenue_proxy=NULL,
  missing_price_rows=1,118.
- Segment changes: 6 rows. CA_3/FOODS_2 had 4,492 units in the last 7 observed
  dates versus 5,284 in the preceding 7 (change −792).
- Forecast errors: e.g. last_value, test horizon 1 has 1,842 observations,
  WMAPE=112.639942%, MAE=1.693268 and RMSE=3.159272.
- Events/prices: 648,455 rows. Item-level observations are retained only in
  ignored local artifacts. Associations do not imply causality.
- Metric provenance: 7 definitions with source table, actual date bounds,
  as_of date, ingestion timestamp and Bronze/Silver IDs.

Concise aggregate query results, provenance and audit counters are in
[real_m5_validation.json](real_m5_validation.json). Full query exports and
comparison snapshots remain under ignored `artifacts/real-validation/`.

## Runtime and resource observations

Profiling completed in **75.837 seconds**. The first monitor followed only the
virtualenv redirector, so its small memory peak is invalid as a pipeline estimate;
an independent process observation saw 1,229.2 MiB peak. Subsequent monitors
sampled the descendant process tree at roughly 250 ms intervals.

| Command run | Seconds | Peak sampled working set MiB | Exit |
| --- | ---: | ---: | ---: |
| bronze-first | 56.685 | 1781.96 | 0 |
| bronze-rerun | 4.529 | 91.22 | 0 |
| silver-initial | 79.778 | 2616.09 | 0 |
| gold-initial | 73.076 | 3260.63 | 0 |
| baseline-first | 246.431 | 1259.42 | 0 |
| baseline-rerun | 214.232 | 1254.66 | 0 |

Independent process observations saw peaks of 3,439.6 MiB for Silver and
4,070.6 MiB for Gold. Available system memory briefly reached 750.90/749.70 MiB,
crossing the supervisor threshold near completion. Both CLIs nevertheless
returned 0 with complete published output; subsequent independent integrity
and quality audits passed. This is a documented memory-headroom limitation,
not a hidden quality failure. Run stages serially and allow several GiB free;
these timings are local observations, not benchmark guarantees.

The existing profiler and pipeline completed, so no components were redesigned.
Verification-helper issues (initial process-memory scope, a SQL alias and a
read-only relation-view operation) were corrected locally; none changed the
pipeline or its persisted business results.

## Regression validation

| Command | Exact result | Exit |
| --- | --- | ---: |
| `python -m pytest` | 53 passed, 1 warning in 58.74s | 0 |
| `python -m pytest -p no:cacheprovider` | 53 passed in 60.85s (0:01:00) | 0 |
| `python -m ruff check .` | All checks passed! | 0 |
| `python -m pip check` | No broken requirements found. | 0 |
| `python scripts/verify.py` | All checks passed!; 53 passed, 1 warning in 62.12s (0:01:02); No broken requirements found. | 0 |
| `git diff --check` | No whitespace errors | 0 |

The pre-existing warning is PytestCacheWarning: local `.pytest_cache/v/cache`
denies writes. It neither fails nor skips tests; the cache-disabled run is
warning-free. `scripts/verify.py` completed its own Ruff/pytest/pip/diff checks.
No ACLs or global configuration changed. Normal CRLF→LF normalization notices
are not diff errors. All 53 synthetic tests remain independent of real data.

The user reported that the earlier hosted CI run had passed. This task did not
trigger a remote workflow or change GitHub state. RP-11 is not declared complete.

## Changes and commits

Updated the derived pilot configuration, real raw manifest, metadata-only sample
provenance, stage evidence, baseline/metric/data documentation, README,
architecture and this report. Added compact aggregate metric CSV and validation
JSON evidence. The six-row real sample was generated and verified locally; it
is not distributed. No source, SQL, tests or dependency files changed. The
sample directory contains tracked guidance and provenance, with generated
row-level files excluded by `.gitignore`.

No implementation bug was found and no fix commit was needed. This evidence is
recorded in one separate local commit, `docs: validate data backbone on real M5`;
its own hash is not embedded in its contents. The existing seven sprint commits
remain unchanged:

```text
0fac514 docs: record data backbone sprint results
35f9aa4 ci: add early validation workflow
4df36e9 feat: implement RP-06 forecasting baselines
e756048 feat: implement RP-05 Gold analytics layer
a5ea2d8 feat: implement RP-04 Silver transformations
d66f142 feat: implement RP-03 Bronze ingestion
f470e36 feat: prepare RP-02 data acquisition and profiling
```

No raw/full generated datasets, caches, `.venv` or ignored artifacts are tracked.
The manifest, aggregate findings, hashes and metadata-only provenance are
versionable evidence. Real row-level samples and item-level query previews are
not distributed. Until redistribution rights are explicitly verified, they
remain local and ignored.
The unpushed real-validation commit was amended before publication to remove
the sample and embedded item-level observations from its reachable history.
All aggregate validation results and RP-02–RP-06 PASS statuses are unchanged.
Local raw files, generated samples and complete validation artifacts are kept.
No push, merge, PR or issue mutation was performed.

## Remaining limitations and next stage

No blocking validation failure remains. Real gates cover this deterministic
3-store × 2-department pilot, not all 10 stores or out-of-sample live retail.
The data is historical; future target actuals are unavailable. Missing prices,
conservative unknown proxy totals, heuristic alert volume and memory headroom
remain explicit limitations. **M5 has no actual inventory data; revenue_proxy
is not audited revenue; spike/event relationships are not causal.**

Recommended next stage after human review: **RP-07**, using these measured
baselines as the comparison. RP-07 has not started. Power BI, advanced ML,
PySpark, AWS, API, agents/Ollama, Streamlit and Docker were not added.

To reproduce from the repository root, reuse `.venv` and the ignored real files:

```powershell
.\.venv\Scripts\python.exe -m retailpulse profile --select-pilot --sample
.\.venv\Scripts\python.exe -m retailpulse bronze
.\.venv\Scripts\python.exe -m retailpulse bronze
.\.venv\Scripts\python.exe -m retailpulse silver
.\.venv\Scripts\python.exe -m retailpulse gold --as-of 2026-10-07
.\.venv\Scripts\python.exe -m retailpulse baseline
.\.venv\Scripts\python.exe -m retailpulse query 03_forecast_errors
.\.venv\Scripts\python.exe scripts/verify.py
git diff --check
git status
```
