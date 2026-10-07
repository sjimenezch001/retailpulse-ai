# RP-06 real-data gate — 2026-10-07

Status: **REAL-DATA VALIDATED — PASS**.

Executed `python -m retailpulse baseline` twice against real Gold run
`20f4dae75fff8e79204e`. Runtime: 246.431 seconds initially,
214.232 seconds on rerun. Sampled process-tree peaks: 1,259.42 and 1,254.66 MiB.

| Phase | Training dates | Evaluation / prediction dates |
| --- | --- | --- |
| Validation | 2011-01-29–2016-03-27 | 2016-03-28–2016-04-24 |
| Test | 2011-01-29–2016-04-24 | 2016-04-25–2016-05-22 |
| Future | 2011-01-29–2016-05-22 | 2016-05-23–2016-06-19 |

Each holdout has 51,576 observations per model (1,842 series × 28 dates).
No random split, within-horizon refit or test-based tuning is used. No future
accuracy is claimed; the 154,728 future predictions have NULL actual values.

| Split | Model | WMAPE | MAE | RMSE |
| --- | --- | ---: | ---: | ---: |
| test | last_value | 105.934365% | 1.795622 | 3.014355 |
| test | rolling_mean | 79.482353% | 1.347252 | 2.361194 |
| test | seasonal_naive_7 | 93.280944% | 1.581142 | 2.789959 |
| validation | last_value | 105.247167% | 1.618602 | 2.915572 |
| validation | rolling_mean | 83.774019% | 1.288365 | 2.190055 |
| validation | seasonal_naive_7 | 100.186588% | 1.540775 | 2.873446 |

WMAPE is displayed as a percentage here and stored as a ratio. MAE/RMSE are
in daily item/store units. Rolling mean has lower measured errors than the
other two baselines on both holdouts; that comparison does not establish
production quality or results on other stores, departments or periods.

Independent SQL recomputed every model's forecast from origin-date history:
last observed value, final seven-day average and repeated prior-week pattern.
There were zero mismatches, duplicate forecast keys, invalid temporal bounds,
invalid values, incorrect actuals, incorrect lineage or overall-metric errors.
All training ends precede targets and all horizons equal target minus origin.

An exact bidirectional `EXCEPT ALL` comparison before/after rerun found **zero
changed rows** across all 464,184 forecast rows and all 222 evaluation rows.
Reruns replace outputs safely without duplication. Existing synthetic tests
also verify that failed evaluation preserves the previous result and that
holdout mutations cannot leak into predictions.

All real aggregate segments have nonzero denominators. A separate diagnostic
slice of 100 real test rows with zero actual units produced WMAPE=NULL and
`wmape_zero_denominator=true`; synthetic tests also exercise this branch. This
slice is a contract check, not a reported business segment or model-quality score.

The [222 segmented error rows](real_m5_baseline_metrics.csv) cover store,
department, demand level and horizons 1–28 for both holdouts and all models.
The forecast CLI query was rerun after persistence and returned 168 horizon
aggregate rows. No implementation defect or dependency change was needed.
Full regression results are recorded in the final sprint report. RP-07 was not
started.
