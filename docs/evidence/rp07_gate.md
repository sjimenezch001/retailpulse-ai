# RP-07 real-data gate — 2026-10-07

Decision: **PASS**. Real M5 LightGBM training, leakage checks, validation-only
selection, freeze-before-test, local MLflow, reproducible reruns and Gold serving
all passed. No model design changed after the final test was disclosed.
The test improves WMAPE/MAE and worsens RMSE; both outcomes are retained.

## Source and predeclared search

Gold source_run_id: `20f4dae75fff8e79204e`. Pilot: 3 stores × 2 departments,
614 items, 1,842 series, 1,941 observed dates. No row-level data is versioned.
Implementation commit: `c0a8e3e83ac10a4788376dc26cb4d118cf2a2a6a`; working tree was
clean at experiment creation. Model environment: LightGBM 4.7.0, Python 3.12.10,
pandas 3.0.6, NumPy 2.5.3, DuckDB 1.5.5. All preexisting dependency pins were
preserved. Added LightGBM, MLflow skinny, SQLAlchemy/Alembic for SQLite, psutil
and their required transitive packages; no scikit-learn, Optuna or SHAP.

[The protocol](../modeling.md) was committed before candidate scoring. It fixed
three candidates, a 730-day fitting window with 28-day warmup, all pilot series,
fixed seeds and 28-day recursive horizons. Each model fit used 1,344,660 targets;
each holdout used 51,576 observations.

| Candidate | Features / objective | Validation WMAPE | MAE | RMSE |
| --- | --- | --- | --- | --- |
| A_core_poisson | core / poisson | 85.346901% | 1.312554 | 2.018481 |
| B_extended_poisson | extended / poisson | 82.312717% | 1.265892 | 1.962028 |
| C_extended_l1 | extended / regression_l1 | 72.730996% | 1.118534 | 2.041508 |

Winner: **C_extended_l1**, 26 extended features, `regression_l1`, 200 trees,
31 leaves, learning rate 0.05, min_data_in_leaf 100, max_bin 127, seed 2026,
four CPU threads and deterministic column-wise histograms. Validation WMAPE
72.730996% beats rolling_mean 83.774019% by
11.043023 percentage points (13.181918% relative).
Validation MAE is 1.118534 and RMSE is 2.041508.

## Evidence of isolation and freeze

The selection function accepts validation records only. The training loader
queries units/prices no later than the forecast origin; the recursive prediction
API has no held-out actuals argument. Test labels are loaded only after the
winner, final fitted model and test predictions are saved. Calendar is known
in advance; no held-out observed prices enter features. Tests mutate current
and future values, inspect recursive inputs, reject invalid temporal bounds
and guard the test-label access path.

Validation: training through 2016-03-27, targets 2016-03-28–2016-04-24.
Test: training through 2016-04-24, targets 2016-04-25–2016-05-22.
Selection never evaluates a candidate on test. The one final winner is retrained
using the frozen window and parameters before test access.

Freeze SHA-256: `7872c99ea7eefef443eb31aca405909c8c222b61424d4f5e28eaeb6a78ead39c`.
Plan SHA-256: `dbf72f66af3639b71120f9558744dabf6f815d67c38d664b25eeae89a28b0b99`.
The checksummed plan records source identity, implementation and model-library
versions. It rejects later configuration changes for the same Gold source.

| Event | UTC timestamp |
| --- | --- |
| plan_created | 2026-10-07T23:04:49.006380+00:00 |
| validation_candidate_completed | 2026-10-07T23:05:28.436993+00:00 |
| validation_candidate_completed | 2026-10-07T23:06:09.164430+00:00 |
| validation_candidate_completed | 2026-10-07T23:06:52.066639+00:00 |
| winner_frozen | 2026-10-07T23:06:52.082597+00:00 |
| validation_reproduction_confirmed | 2026-10-07T23:08:07.335057+00:00 |
| final_model_trained | 2026-10-07T23:09:16.453246+00:00 |
| test_evaluation_started | 2026-10-07T23:09:16.483172+00:00 |
| test_evaluation_completed | 2026-10-07T23:09:16.716620+00:00 |
| gold_persisted | 2026-10-07T23:09:22.817411+00:00 |

There is exactly **one** test-evaluation start and completion. Before it,
independent validation retraining reproduced all 51,576 predictions and the
native model bytes exactly. Successful CLI rerun returned `reused=true`,
preserved artifact hashes and created no additional MLflow runs or test events.
An interrupted test without saved results fails closed in the integration test.

## One-time test and segmented diagnostics

| Metric | LightGBM | rolling_mean | ML minus baseline | Relative change |
| --- | --- | --- | --- | --- |
| WMAPE | 74.825958% | 79.482353% | -4.656394 percentage points | 5.858400% improvement |
| MAE | 1.268324 | 1.347252 | -0.078927 | 5.858400% improvement |
| RMSE | 2.431177 | 2.361194 | +0.069983 | 2.963866% degradation |

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

All store, department and demand-level WMAPEs improve; their RMSEs worsen.
Best horizon improvements and every WMAPE regression:

| Horizon | ML WMAPE | Baseline WMAPE | Difference (pp) |
| --- | --- | --- | --- |
| 3 | 78.098462% | 92.824769% | -14.726307 |
| 18 | 79.924180% | 93.790536% | -13.866357 |
| 4 | 77.897190% | 91.056154% | -13.158963 |
| 13 | 71.986225% | 71.869271% | +0.116954 |
| 27 | 74.347858% | 72.037030% | +2.310828 |
| 21 | 74.422055% | 71.761756% | +2.660299 |
| 28 | 74.427390% | 71.099088% | +3.328302 |

[The complete aggregate comparison](rp07_metrics.csv) contains 74 rows for
both splits, all 28 horizons, stores, departments, demand levels and overall
metrics. Metrics use the RP-06 ratio-of-totals definition of WMAPE. Segment
thresholds use full observed history through each origin and match RP-06.
No segment diagnosis led to changes in features or parameters.

## Frozen model importance

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

[All 26 importance values](rp07_feature_importance.csv) are retained. Gain is
not a causal effect and is affected by correlated features and item identity.

## Gold reconciliation and local tracking

Gold contains **567,336 forecasts**: 464,184 unchanged RP-06 baseline forecasts
plus 103,152 ML forecasts. It has **296 evaluation rows** (222 baseline + 74 ML)
and one `model_run` entry. Full-grain uniqueness passes. Count, row-hash XOR and
row-hash sum fingerprints confirm baseline forecasts, metrics and run metadata
are unchanged. Transactional replacements are scoped by model; synthetic tests
also rerun baselines after ML and verify preservation in both directions.
The existing forecast-error business query serves all 56 ML split/horizon rows.

MLflow experiment: **RetailPulse-RP07**.

| Run | MLflow run ID |
| --- | --- |
| A_core_poisson | `9957d4715083451d8244e8135e54c847` |
| B_extended_poisson | `a84509b19cd64310bce268361b23ba5f` |
| C_extended_l1 | `bee906ed856440f5b08dbae5c9fe38d7` |
| Frozen final model | `5e5ccd6aca564bcb9e16bf240f7a02aa` |

All four runs are FINISHED and contain model.txt, categories.json,
importance.csv, training.json and metadata.json. Run metadata includes git
revision, Gold source, exact features, windows, parameters, metrics, timings,
memory observations and dependencies. Local paths:

- `artifacts/mlflow/mlflow.db`
- `artifacts/mlflow/artifacts/<run_id>/artifacts/`
- `artifacts/rp07/20f4dae75fff8e79204e/`

No MLflow server or external service was required. Raw files, samples,
row-level forecasts and model artifacts remain local and Git-ignored.
[Machine-readable evidence](rp07_validation.json) retains hashes, freeze,
aggregate measurements, run IDs, audit order and reproducibility checks.

## Resource observations

| Stage | Fit seconds | Load/train/predict seconds | Sampled peak RSS (MiB) |
| --- | --- | --- | --- |
| A_core_poisson | 27.256 | 30.773 | 506.84 |
| B_extended_poisson | 36.279 | 40.184 | 725.72 |
| C_extended_l1 | 38.434 | 42.016 | 746.84 |
| Frozen final model | 32.316 | 35.798 | 694.61 |
| Independent validation reproduction | 33.992 | 36.620 | 597.15 |

The three candidate load/train/predict stages plus final fit took
148.771 seconds;
independent validation reproduction added 36.620 seconds.
Peak observed training-process RSS was
746.84 MiB.
Sampling was every 100 ms and excludes other processes. Stage timings exclude
MLflow initialization/logging and final Gold persistence; they are not a full
end-to-end wall-clock benchmark. All fits ran serially.

## Validation and limitations

- `python -m pytest -p no:cacheprovider`: **63 passed** in 55.56 seconds.
- `python -m ruff check .`: **PASS**.
- `python -m pip check`: **No broken requirements found**.
- `python scripts/verify.py`: **PASS**, including 63 tests in 51.13 seconds.
- `git diff --check`: **PASS**.
- Independent validation retraining: exact predictions and model bytes.
- Completed model command rerun: cached results, identical hashes, no duplicates
  and no additional test evaluation or MLflow run.

Tests report an upstream MLflow/SQLAlchemy deprecated-loader warning. The
verification script also reports a nonfatal inability to write the existing
local pytest cache; its checks still succeed. No functional failure is hidden.

The [model card](../model_card.md) records missing prices (977,382 rows,
27.336894%, all zero units), historical-data and no-inventory limits, noncausal
price/event interpretation, recursive uncertainty and the RMSE regression.
This single historical holdout does not prove production robustness.

Outstanding blockers: **none for RP-07**. Recommended next stage is RP-08
(Power BI), subject to a separate request. RP-08 was not started. No push or
merge was performed; changes are retained in focused local commits.
