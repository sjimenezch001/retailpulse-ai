# RP-06 forecasting baselines

These are reference algorithms, not advanced ML or evidence of production model
quality. Real M5 pilot measurements are recorded below.

`python -m retailpulse baseline` reads daily Gold sales and performs a fixed
chronological split: final 28 dates for test, preceding 28 for validation, all
previous dates for train (at least 28). `--validation-days`, `--test-days` and
`--rolling-window` make the windows explicit. Random splits are never used.
The panel must have unique keys and complete common daily history.

Validation predictions use train only. Test predictions use train + validation,
which are already observed at the later test origin. Neither origin is updated
inside its forecast horizon. All three models are reported on both holdouts;
no winner is chosen using the test set. Future forecasts retrain on all observed
history and have NULL actual units, so no future quality numbers are reported.

- `last_value`: repeat the last observed value for every horizon step.
- `rolling_mean`: repeat the mean of the final 7 training days by default;
  never include holdout observations in that mean.
- `seasonal_naive_7`: repeat the final training week's weekday pattern. For
  horizons beyond 7 days, repeat that same historical week; do not read the
  preceding holdout week. Requires at least 7 observed training dates.

## Metrics and segmentation

WMAPE is `sum(abs(actual - predicted)) / sum(abs(actual))`, stored as a ratio
(multiply by 100 only for percentage display). A zero denominator always yields
NULL/None with `wmape_zero_denominator = true`, even for perfect all-zero
predictions. MAE and RMSE remain defined. Metric inputs must be aligned,
nonempty, finite and nonnegative. Segment WMAPE aggregates absolute errors and
actual totals directly; it is not the mean of item-level WMAPE values.

Errors are reported overall and separately by store, department, demand level
and horizon. Demand levels use each series' training-only mean: `zero` = 0,
`low` = (0, 1), `medium` = [1, 10), `high` = [10, infinity). These fixed thresholds
avoid fitting segments on holdout data; no commercial meaning is implied.

`fact_forecast` stores model, split, origin, target, horizon, actual/predicted
units, segment, training bounds and Gold run ID. `forecast_evaluation` contains
segmented errors. `baseline_run` records exact temporal boundaries, parameters,
algorithm version and execution timestamp. `--future-horizon` defaults to 28.
The run replaces only its three baseline models transactionally; reruns do not
duplicate forecasts or erase RP-07 ML forecasts. A failed evaluation leaves
earlier database results intact.

To inspect results after a run:

```powershell
.\.venv\Scripts\python.exe -m retailpulse query 03_forecast_errors
```

## Real M5 evaluation — 2026-10-07

Pilot: `CA_1`, `CA_2`, `CA_3` × `FOODS_1`, `FOODS_2` (1,842 series).
Each model has 51,576 observations per holdout. Initial training covers
2011-01-29–2016-03-27. Validation is 2016-03-28–2016-04-24; test is
2016-04-25–2016-05-22. The test origin retrains through 2016-04-24.

| Split | Model | WMAPE (percentage display) | MAE (units) | RMSE (units) |
| --- | --- | ---: | ---: | ---: |
| test | last_value | 105.934365% | 1.795622 | 3.014355 |
| test | rolling_mean | 79.482353% | 1.347252 | 2.361194 |
| test | seasonal_naive_7 | 93.280944% | 1.581142 | 2.789959 |
| validation | last_value | 105.247167% | 1.618602 | 2.915572 |
| validation | rolling_mean | 83.774019% | 1.288365 | 2.190055 |
| validation | seasonal_naive_7 | 100.186588% | 1.540775 | 2.873446 |

Rolling mean has the lowest measured WMAPE, MAE and RMSE among these three
baselines on both holdouts. This is a comparison on this pilot and these dates,
not a production-quality or generalization claim. WMAPE can exceed 100%; it is
not an accuracy score bounded at 100%. No winner was selected or tuned on test.

The [complete segmented measurements](evidence/real_m5_baseline_metrics.csv)
contain 222 aggregate rows covering store, department, training-derived demand
level and horizons 1–28, for all three models and both holdouts. WMAPE is stored
as a ratio in that CSV. The real aggregate segments have no zero denominators;
synthetic tests still exercise the explicit undefined-WMAPE branch.

The Gold-compatible output has 464,184 rows: 154,728 each for validation, test
and future. Future dates are 2016-05-23–2016-06-19, with NULL actuals and no
claimed future metrics. Full-grain independent SQL verifies the last value,
seven-day mean and prior-week cycle using observations at or before each origin.
See [RP-06 evidence](evidence/rp06_gate.md) for rerun and regression checks.
