# RP-07 forecasting protocol

This protocol is declared before real candidate evaluation. Selection uses only
validation WMAPE. MAE and RMSE are diagnostics. The final test cannot change
the feature set, model family, objective, parameters, training window or clipping.

## Predeclared candidates

| Candidate | Features | Objective | Trees | Leaves | Learning rate |
| --- | --- | --- | ---: | ---: | ---: |
| A_core_poisson | Identity, calendar, lags | Poisson | 200 | 31 | 0.05 |
| B_extended_poisson | Core + rolling, past prices, events, SNAP | Poisson | 200 | 31 | 0.05 |
| C_extended_l1 | Same extended features | Absolute error | 200 | 31 | 0.05 |

All candidates use seed 2026, four CPU threads, `min_data_in_leaf=100`,
`max_bin=127`, a 128 MiB histogram cache, `deterministic=true`, and
`force_col_wise=true`. There is no early stopping, random search, row sampling,
deep learning or XGBoost comparison. Native LightGBM avoids a scikit-learn
dependency. [LightGBM documents](https://lightgbm.readthedocs.io/en/stable/Parameters.html#deterministic)
the deterministic CPU and histogram settings; exact cross-version/platform
equality is not promised.

The most recent **730 target days**, plus 28 days of lag warmup, bound each
training matrix. This resource choice precedes candidate scoring: two annual
cycles provide seasonal coverage while avoiding the entire 3.5-million-row
Gold frame. Training stages run serially. Every pilot series is included and
every one of the 28 holdout dates is evaluated; test is never subsampled.

## Temporal contract and information availability

| Split | Latest training observation / forecast origin | Targets |
| --- | --- | --- |
| Validation | 2016-03-27 | 2016-03-28–2016-04-24 |
| Test | 2016-04-24 | 2016-04-25–2016-05-22 |

`features/forecast.py` reads only units and prices at or before the origin.
Identity categories are learned from origin-time series metadata. One-day
training targets use `lag_1`, `lag_7`, `lag_14`, `lag_28`; all rolling moments
end at t-1. Standard deviations use the population definition (`ddof=0`).
Calendar features are weekday, day, ISO week, month, year and weekend.
The extended set adds three rolling means (7/14/28), two standard deviations
(7/28), lagged price, missing-price flag, lagged price change, two event flags
and the state-specific SNAP indicator. Published calendar and SNAP schedules
are assumed known in advance; there is no causal interpretation.

Forecasts remain fixed-origin for 28 days. At each step the model feeds its
own prediction into subsequent lag/rolling features. It never reads actual
sales from within the horizon. Negative numerical predictions are clipped
to zero under the same rule for every candidate. Future observed prices are
excluded: retain the last observed daily price (including missingness), use
the last historical change for horizon 1, then zero change for an unchanged
known price. Missing changes remain missing. Price uncertainty is a limitation.

Demand-level segments reuse RP-06 thresholds and the full-history mean through
each origin, independently of the bounded model-fitting window.

## Freeze, evaluation and reruns

```powershell
.\.venv\Scripts\python.exe -m retailpulse model --validation-only
.\.venv\Scripts\python.exe -m retailpulse model
```

The first command saves the three validation results and the lowest-WMAPE
winner in `artifacts/rp07/<Gold source_run_id>/freeze.json`. Ties use candidate
name for a deterministic decision. The frozen design includes features,
parameters, windows, source identity, an implementation checksum and the
selection metric. The immutable plan also records model-library versions.
Git revision, environment and timestamps are retained for audit.

The second command reuses that selection, fits only the frozen winner through
the test origin, writes predictions, and then opens test actuals once. A
durable evaluation marker and ordered audit events prove the sequence. A
failure after opening test but before saving results stops automatic retries
for inspection. There is no force-reset or retuning flag. Do not remove these
records to bypass the holdout contract.

Successful reruns verify artifact checksums and re-persist saved forecasts
without retraining, rescoring test, or creating new MLflow runs. A changed
model plan for the same Gold source is rejected. Synthetic tests separately
verify deterministic retraining and native model save/load. Reproducing the
experiment in a new environment must retain the published frozen design;
this is verification, not permission to tune against the disclosed test.

## Tracking and Gold

`mlflow-skinny` provides local tracking; SQLAlchemy and Alembic provide the
SQLite backend, and psutil samples process RSS every 100 ms. All tracking
metadata lives in `artifacts/mlflow/mlflow.db`, with model text, category maps,
feature importance and environment artifacts alongside it. No server or
credentials are required. This follows the documented
[local database tracking setup](https://mlflow.org/docs/latest/self-hosting/architecture/backend-store/).
Each candidate and the final model has its own MLflow run. MLflow's transitive
web dependencies do not implement an application API in this stage.

The stable Gold model name is `lightgbm_global_v1`. Validation and test forecasts
coexist with all three RP-06 baselines in `fact_forecast` and
`forecast_evaluation`; `model_run` links the source, freeze checksum and MLflow
run. Replacements are transactional and scoped by model, so reruns preserve
other models and do not duplicate the forecast grain. Existing baseline future
forecasts remain available; RP-07 does not add a separate future-serving model.

Only aggregate metrics, protocol and model documentation are versioned.
Real row-level forecasts, samples, model binaries and MLflow runtime files stay
Git-ignored. Training code and tests contain only synthetic observations.
