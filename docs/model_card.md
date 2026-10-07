# RetailPulse AI model card — RP-07

Status: **PASS**, evaluated on 2026-10-07. Stable model: `lightgbm_global_v1`.

## Purpose, data and target

A global tabular model predicts nonnegative daily `units` at store/item grain
over a fixed-origin 28-day horizon. It supports a historical retail analytics
portfolio; it is not a live replenishment policy or an inventory-demand model.
The real M5 pilot is CA_1, CA_2, CA_3 × FOODS_1, FOODS_2: 614 items, 1,842
series, 1,941 observed dates and 3,575,322 daily Gold rows. Gold source_run_id:
`20f4dae75fff8e79204e`. Each holdout includes all **51,576** observations.

## Temporal design and features

Validation training ends 2016-03-27; targets are 2016-03-28–2016-04-24.
Final training ends 2016-04-24; test targets are 2016-04-25–2016-05-22.
The fixed 730-day fitting window uses 1,344,660 rows at each origin, with
28 additional warmup days. Validation fitting targets span 2014-03-29–2016-03-27;
final fitting targets span 2014-04-26–2016-04-24. This memory bound was declared
before candidate scoring, and no test observations were dropped.

The 26 features are:

- Identity: store_id, item_id, dept_id, cat_id, state_id (categorical).
- Calendar: day_of_week, day_of_month, week_of_year, month, year, weekend.
- History: lag_1, lag_7, lag_14, lag_28; rolling_mean_7, rolling_mean_14,
  rolling_mean_28; rolling_std_7, rolling_std_28.
- Other: sell_price_lag_1, price_missing_lag_1, price_change_pct_lag_1,
  event_1, event_2 and state-specific snap.

All lag, rolling and price features exclude the target day. At forecast time,
only previous predictions enter within-horizon history. Calendar/SNAP schedules
are assumed known; observed future prices are excluded and the origin price is
carried forward. See [the full protocol](modeling.md) for exact definitions.

## Selection and frozen configuration

| Candidate | Features / objective | Validation WMAPE | MAE | RMSE |
| --- | --- | --- | --- | --- |
| A_core_poisson | core / poisson | 85.346901% | 1.312554 | 2.018481 |
| B_extended_poisson | extended / poisson | 82.312717% | 1.265892 | 1.962028 |
| C_extended_l1 | extended / regression_l1 | 72.730996% | 1.118534 | 2.041508 |

Winner: **C_extended_l1**, selected solely by validation WMAPE. Baseline
validation WMAPE is **83.774019%**; the winner improves it by
11.043023 percentage points (13.181918% relative).
All candidates used 200 trees, 31 leaves, learning rate 0.05, minimum leaf size
100, max_bin 127, four CPU threads and seed 2026. The winner uses
`objective=regression_l1`, deterministic column-wise training and the extended
feature set. No early stopping or additional tuning followed selection.

The design was frozen at `2026-10-07T23:06:52.068634+00:00` before final retraining and
test access. Freeze SHA-256: `7872c99ea7eefef443eb31aca405909c8c222b61424d4f5e28eaeb6a78ead39c`.
Independent validation retraining reproduced all predictions and native model
bytes exactly before the test was opened. The final design remained unchanged
after seeing test results.

## Final one-time test

| Metric | LightGBM | rolling_mean | ML minus baseline | Relative change |
| --- | --- | --- | --- | --- |
| WMAPE | 74.825958% | 79.482353% | -4.656394 percentage points | 5.858400% improvement |
| MAE | 1.268324 | 1.347252 | -0.078927 | 5.858400% improvement |
| RMSE | 2.431177 | 2.361194 | +0.069983 | 2.963866% degradation |

Absolute-error performance improves while squared-error performance worsens.
An absolute-error objective emphasizes conditional medians and can underpredict
large demand peaks. These results do not establish a universally superior model.

## Segmented test performance

| Segment type | Segment | Observations | ML WMAPE | Baseline WMAPE | Difference (pp) |
| --- | --- | --- | --- | --- | --- |
| store | CA_1 | 17192 | 77.687926% | 84.248553% | -6.560628 |
| store | CA_2 | 17192 | 74.583999% | 78.989753% | -4.405754 |
| store | CA_3 | 17192 | 72.863231% | 76.296693% | -3.433462 |
| department | FOODS_1 | 18144 | 77.331042% | 81.823526% | -4.492484 |
| department | FOODS_2 | 33432 | 72.951091% | 77.730160% | -4.779068 |
| demand_level | high | 560 | 50.597641% | 51.518448% | -0.920808 |
| demand_level | low | 32872 | 88.334768% | 98.399092% | -10.064324 |
| demand_level | medium | 18144 | 69.708900% | 71.612838% | -1.903938 |

WMAPE improves for all reported stores, departments and demand levels. The
largest demand-level improvement is the low group; all eight of these segments
have worse RMSE, as recorded in the complete metric export.

Best horizon improvements and **all four WMAPE regressions**:

| Horizon | ML WMAPE | Baseline WMAPE | Difference (pp) |
| --- | --- | --- | --- |
| 3 | 78.098462% | 92.824769% | -14.726307 |
| 18 | 79.924180% | 93.790536% | -13.866357 |
| 4 | 77.897190% | 91.056154% | -13.158963 |
| 13 | 71.986225% | 71.869271% | +0.116954 |
| 27 | 74.347858% | 72.037030% | +2.310828 |
| 21 | 74.422055% | 71.761756% | +2.660299 |
| 28 | 74.427390% | 71.099088% | +3.328302 |

All 28 horizons and both splits, including MAE/RMSE, are available in
[the aggregate metric comparison](evidence/rp07_metrics.csv). Positive
ML-minus-baseline differences mean degradation. No segment finding was used
to retune the frozen model.

## Feature importance

| Rank | Feature | Gain | Share of total gain |
| --- | --- | --- | --- |
| 1 | item_id | 2807717.937 | 35.656% |
| 2 | rolling_mean_28 | 1641105.255 | 20.841% |
| 3 | rolling_mean_14 | 1115316.848 | 14.164% |
| 4 | rolling_mean_7 | 1022898.529 | 12.990% |
| 5 | day_of_week | 544624.461 | 6.916% |
| 6 | lag_1 | 387634.622 | 4.923% |
| 7 | day_of_month | 181990.038 | 2.311% |
| 8 | lag_28 | 78362.971 | 0.995% |
| 9 | rolling_std_28 | 43131.050 | 0.548% |
| 10 | rolling_std_7 | 35382.165 | 0.449% |

Gain importance is a model diagnostic, **not causal explanation**. Correlated
lag/rolling features share signal, and categorical item identity can capture
series-specific patterns without demonstrating generalization to new items.
[All feature importances](evidence/rp07_feature_importance.csv) are available.

## Limitations

- Historical M5 data and a single validation/test pair do not establish current
  production performance or stability across other stores and periods.
- 977,382 pilot price rows are missing (27.336894%); all have zero observed
  units. Missingness may encode availability patterns. Future prices are
  unknown and held at their origin values for forecasting.
- M5 provides no actual inventory observations. Zero sales are not proof of
  stockouts or zero demand, and forecasts are not inventory recommendations.
- Price/event/SNAP associations are noncausal. Calendar availability is an
  explicit historical experiment assumption, not a live integration.
- Recursive errors accumulate; four horizons regress in WMAPE and overall
  RMSE worsens. The bounded training window omits older history.
- Categories require known series; cold-start items and intervals are not
  supported. No probabilistic calibration or production deployment is claimed.

## Reproducibility, resources and tracking

Use the existing Python 3.12 environment, install `requirements.txt`, and follow
[the protocol commands](modeling.md#freeze-evaluation-and-reruns). A completed
`python -m retailpulse model` reuses checksummed artifacts; it does not retrain
or rescore test. Code and environment identity are fixed in the local plan.
Keep that plan and freeze when verifying in another environment; do not use
the disclosed test to revise the design.

| Stage | Fit seconds | Load/train/predict seconds | Sampled peak RSS (MiB) |
| --- | --- | --- | --- |
| A_core_poisson | 27.256 | 30.773 | 506.84 |
| B_extended_poisson | 36.279 | 40.184 | 725.72 |
| C_extended_l1 | 38.434 | 42.016 | 746.84 |
| Frozen final model | 32.316 | 35.798 | 694.61 |
| Independent validation reproduction | 33.992 | 36.620 | 597.15 |

RSS was sampled every 100 ms in the training process and may miss shorter peaks.
These stage timings include loading, fitting, prediction and model saving, but
exclude MLflow initialization/logging and final persistence. Float32 histories,
categoricals and bounded reads keep the full Gold frame out of Python memory.

MLflow experiment: **RetailPulse-RP07**, backed by local
`artifacts/mlflow/mlflow.db`; no server is required.

| Run | MLflow run ID |
| --- | --- |
| A_core_poisson | `9957d4715083451d8244e8135e54c847` |
| B_extended_poisson | `a84509b19cd64310bce268361b23ba5f` |
| C_extended_l1 | `bee906ed856440f5b08dbae5c9fe38d7` |
| Frozen final model | `5e5ccd6aca564bcb9e16bf240f7a02aa` |

Artifacts: `artifacts/mlflow/artifacts/<run_id>/artifacts/` and
`artifacts/rp07/20f4dae75fff8e79204e/`. Native model, category maps, importance, parameters,
windows, git revision and environment metadata are logged. Forecasts and
models remain ignored; only aggregates and provenance are distributed.
Gold serves 103,152 ML forecasts beside all 464,184 unchanged baseline
forecasts. RP-08 has not started. See [gate evidence](evidence/rp07_gate.md).
