# RP-06 gate — 2026-10-07

Status: CODE COMPLETE; REAL-DATA VALIDATION PENDING.

Implemented fixed-origin last value, trailing mean and previous-week seasonal
naive baselines. Chronological train/validation/test boundaries are explicit;
validation uses train, test uses the later train+validation history, and future
forecasts use all observed history. There is no within-horizon refit or random
split. All models are reported; the test set is not used to choose a winner.

WMAPE, MAE and RMSE are tested against hand calculations. Zero-denominator
WMAPE is undefined (NULL/None) with an explicit flag. Errors are segmentable by
store, department, training-only demand level and horizon. Gold forecast rows
record dates, origin, training range, model, split and upstream Gold run ID.
Writes replace baseline outputs atomically and reruns do not duplicate rows.

Validation: `python -m pytest -p no:cacheprovider` → `51 passed in 9.73s`;
`python -m ruff check .` → `All checks passed!`.
Tests mutate holdout observations to prove predictions/segments cannot leak,
check multiweek seasonal behavior, reject incomplete panels and verify the
Gold interface, reconciliation and preservation of earlier results on failure.

Synthetic fixtures validate algorithms only. Real M5 forecasting metrics and
baseline quality comparisons are pending; no model-quality numbers are claimed.
Dependencies are unchanged. RP-07 has not started.
