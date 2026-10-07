# RP-06 forecasting baselines

These are reference algorithms, not advanced ML or evidence of production model
quality. No real M5 metrics have been measured in this sprint.

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
The run replaces its prior results transactionally; reruns do not duplicate
forecasts. A failed evaluation leaves earlier database results intact.

To inspect results after a run:

```powershell
.\.venv\Scripts\python.exe -m retailpulse query 03_forecast_errors
```

All current validation uses explicitly synthetic fixtures. Real-data metrics,
baseline comparisons and scale behavior remain pending real M5 execution.
