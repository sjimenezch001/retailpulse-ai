# RP-08 dashboard gate — 2026-10-07

**RP-08 ENGINEERING: PASS. RP-08 FULL GATE: PASS.**

The local serving layer, native semantic model and all three Power BI pages
were implemented and verified. Actual Desktop renders, native filter/navigation
checks, SQL reconciliation, live DAX queries and a genuine PBIX save/reopen
passed. No manual completion is outstanding. Nothing was pushed, merged or
published. RP-09/RP-10 were not started.

## Automation and artifacts

Power BI Desktop 2.158.1304.0, Node 24.11.1, Microsoft's report authoring CLI
0.5.0, Desktop Bridge CLI 1.0.0 and TOM 19.117.0 were operational. The official
[Power BI Report skill](https://github.com/microsoft/skills-for-fabric/blob/main/plugins/powerbi-authoring/skills/powerbi-report-cli/SKILL.md)
guided native report authoring. Definitions were generated programmatically;
TOM serialized and round-tripped the model. Microsoft's report validator
returned **0 errors, 0 warnings**. The local structure validator checked
**3 pages, 49 native visual containers, 15 tables, 14 relationships and 34 DAX measures**.

Desktop Bridge opened/reloaded the local PBIP and captured the genuine pages.
Import partitions were processed through the supported local TOM API. Windows
accessibility controls exercised slicers, navigation and native Save As.
The normal Desktop Refresh/Save As workflow is documented in the build guide.

The initial sandbox-launched Desktop process did not initialize its UI. Running
Desktop as the normal Windows user resolved this. A second issue exposed private
Windows permissions on files moved from Python's temporary directory: export
publication now copies into the output directory before atomic replacement,
so Desktop inherits read access. All 15 partitions then reached Ready.

The actual saved binary was placed at ignored
`dashboards/powerbi/RetailPulse.pbix` and reopened in a separate Desktop process.
It contains **5,297,500 bytes**. SHA-256:
`6f46c3c4036deea2f267ff6cf97523b649faebf70288df6579b976c87c0236f6`.
The reopened file path was confirmed by the connected Desktop Bridge; all three
page tabs were present and its independently loaded model passed all 16 DAX
checks again. This is a Desktop-produced binary, not a generated placeholder.

## Data, provenance and independent reconciliation

Gold `20f4dae75fff8e79204e` → Silver `3bb14677a2a3a1205013` → Bronze
`47b8b962c868f3c60fc8`. Pilot: CA_1/CA_2/CA_3, FOODS_1/FOODS_2,
614 products, 1,842 series, 1,941 observed dates (2011-01-29–2016-05-22).
Gold's `as_of_date` is 2026-10-07; historical freshness is 3,790 days.

Gold contains 3,575,322 daily observations, 1,668 store-week records,
380,925 spike flags, 567,336 forecasts, 296 evaluation records and one frozen
model run. The BI forecast import excludes 154,728 future rows with unknown
actuals. Its four models coexist over validation and test.

| Export | Rows | Grain |
| --- | ---: | --- |
| date | 1,941 | Observed date |
| week | 278 | Observed week |
| store / department / product | 3 / 2 / 614 | Dimension key |
| model / split / demand_level / horizon | 4 / 2 / 3 / 28 | Dimension key |
| sales_daily | 11,646 | Date/store/department |
| sales_product_week | 512,076 | Week/store/product |
| forecast | 412,608 | Origin/target/store/product/model/split |
| metadata | 1 | Gold snapshot |

All 13 dataset SHA-256 values, byte sizes, lineage, source counts, aggregate
metrics, Gold hash and frozen-artifact hashes are in
[rp08_data_audit.json](rp08_data_audit.json). Manifest SHA-256:
`a89a2dedf49c4946b9ab23e705f479ebbcf0beff35518c5958e4ee8d9ce3da32`.
Repeated exports are deterministic. Gold is opened read-only; the real model
was not retrained and prior-stage artifacts were preserved.

SQL reconciliation verifies units, observation counts, price coverage, revenue
null semantics, spikes, date bounds, dimensions, forecast rows/uniqueness,
horizons, WMAPE/MAE/RMSE and lineage. Independent comparisons of **exported CSV
values** against Gold passed for 6 date/store/department groups, 1,842
store/product groups and 3,808 model/split/store/department/demand/horizon groups.

Full-history units are **4,530,250**. Known-price partial revenue is
**13,500,903.56**; canonical complete revenue remains NULL because **977,382**
observations lack prices. Price coverage is **72.6631055888%**. Unknown prices
are never presented as known zero revenue.

| Full test metric | Frozen LightGBM | Rolling mean |
| --- | ---: | ---: |
| WMAPE | 74.8259583508% | 79.4823526336% |
| MAE | 1.2683243673 | 1.3472517672 |
| RMSE | 2.4311766200 | 2.3611939984 |

The dashboard retains the RMSE regression. Selection, forecast values, frozen
model parameters and RP-02–RP-07 results were not changed.

## Desktop and interaction evidence

[Live project DAX results](rp08_desktop_validation.json) and
[reopened PBIX DAX results](rp08_pbix_validation.json) each contain 16 passing
SQL-backed checks. They cover full and filtered sales, weekly product context,
every model/split, combined forecast slicers, model-independent actual totals,
comparison filter isolation, empty selections and independent fact filtering.

Native UI checks produced the expected values:

| Interaction | Observed result | Independent expectation |
| --- | --- | --- |
| Executive store CA_1, default 56-day range | 47,850 units | 47,850 |
| CA_1 + FOODS_1 + 2016-04-25–2016-05-22 | 9,587 units | 9,587 |
| Diagnostics CA_2 + FOODS_1 + FOODS_1_001, default week range | 52 units | 52 |
| Forecast model Rolling mean, test | 79.48% WMAPE | 79.4823526336% |
| Rolling mean, test, horizon 7, low demand | 82.84% WMAPE | 82.8448892066% |
| Same selection, validation split | 86.27% WMAPE | 86.2736972962% |

Ctrl+click on the native page navigator moved from Executive to Diagnostics
and then Forecast Performance. Defaults were restored through supported PBIR
reload after saving the interaction session. Screenshots show those defaults.

The following images are unmodified Desktop Bridge captures of real rendered
pages, inspected for errors, missing content, clipping, values and caveats:

![Executive Overview](rp08/Executive%20Overview.png)

![Store and Product Diagnostics](rp08/Store%20%26%20Product%20Diagnostics.png)

![Forecast Performance](rp08/Forecast%20Performance.png)

All native visuals rendered. Required disclosures and model comparisons are
visible. Product ranks and weekly context retain native vertical scrolling;
no rows were removed to fit the screenshot. Regional date abbreviations and
number separators come from this Windows Desktop locale; authored content is
English. Boundary weeks are explicitly described as potentially partial.

## Checks and scope

- `python -m pytest -p no:cacheprovider`: **75 passed** (12 new BI tests).
- `python -m ruff check .`: **All checks passed**.
- `python -m pip check`: **No broken requirements found**.
- `python scripts/verify.py`: **PASS**, including 75 tests.
- `git diff --check`: **PASS**.
- Official report schema/formatting validation: **0 errors, 0 warnings**.
- TMDL round trip, local structure checks, SQL reconciliation, live DAX and
  reopened-PBIX DAX: **PASS**.

Existing MLflow/SQLAlchemy emits a `noload` deprecation warning during its
synthetic integration test. The verification wrapper also reports an existing
pytest-cache permission warning in this agent environment; tests and the
script exit successfully. The explicitly requested cache-disabled test run
has no cache warning. No dependency pins were changed or tests weakened.

Public files contain reusable definitions, code, synthetic tests and aggregate
evidence. CSV imports, raw M5, real samples, local paths, caches, frozen model
binaries and the data-filled PBIX remain ignored. No publication or sign-in
occurred. The branch is `feat/rp-08-powerbi`; implementation commits are local.
