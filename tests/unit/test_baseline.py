from math import sqrt

import pandas as pd
import pytest

from retailpulse.models.baseline import (
    evaluate_baselines,
    predict_baselines,
    temporal_split,
    validate_panel,
)
from retailpulse.models.metrics import forecast_metrics, segmented_metrics
from retailpulse.quality.checks import QualityError
from retailpulse.transforms.silver import build_silver


def panel(sources):
    return build_silver(sources, ["SYN_A", "SYN_B", "SYN_C"], ["SYN_D1", "SYN_D2"])["fact_sales_daily"]


def test_metrics_hand_calculated():
    scores = forecast_metrics([1, 2, 3], [2, 2, 1])
    assert scores["WMAPE"] == pytest.approx(0.5)
    assert scores["MAE"] == 1.0
    assert scores["RMSE"] == pytest.approx(sqrt(5 / 3))
    assert not scores["wmape_zero_denominator"]


@pytest.mark.parametrize("predicted", [[0, 0], [1, 2]])
def test_zero_denominator_is_explicit(predicted):
    scores = forecast_metrics([0, 0], predicted)
    assert scores["WMAPE"] is None
    assert scores["wmape_zero_denominator"]
    assert scores["MAE"] >= 0


@pytest.mark.parametrize("actual,predicted", [([], []), ([1], []), ([float("nan")], [1]),
                                           ([1], [float("inf")]), ([-1], [1])])
def test_invalid_metric_inputs_rejected(actual, predicted):
    with pytest.raises(QualityError):
        forecast_metrics(actual, predicted)


def test_time_split_is_visible_and_disjoint(sources):
    splits = temporal_split(panel(sources), validation_days=7, test_days=7)
    assert splits["train"]["date"].nunique() == 28
    assert splits["train"]["date"].max() < splits["validation"]["date"].min()
    assert splits["validation"]["date"].max() < splits["test"]["date"].min()
    assert sum(len(part) for part in splits.values()) == 252


def test_baseline_values_and_multistep_weekly_pattern(sources):
    training = temporal_split(panel(sources), 7, 7)["train"]
    result = predict_baselines(training, 14, split="future", source_run_id="synthetic")
    block = result[(result["store_id"] == "SYN_A") & (result["item_id"] == "SYN_ITEM1")]
    assert block.loc[block["model"] == "last_value", "predicted_units"].tolist() == [7.] * 14
    assert block.loc[block["model"] == "rolling_mean", "predicted_units"].tolist() == [4.] * 14
    assert block.loc[block["model"] == "seasonal_naive_7", "predicted_units"].tolist() == list(range(1, 8)) * 2
    assert (result["target_date"] > result["training_end"]).all()
    assert result["actual_units"].isna().all()


def test_future_mutations_do_not_change_validation_predictions(sources):
    original = panel(sources)
    altered = original.copy()
    altered.loc[altered["date"] > pd.Timestamp("2020-01-28"), "units"] = 9000
    first, _, windows = evaluate_baselines(original, source_run_id="test", validation_days=7, test_days=7)
    second, _, _ = evaluate_baselines(altered, source_run_id="test", validation_days=7, test_days=7)
    columns = ["predicted_units", "demand_level", "training_start", "training_end"]
    pd.testing.assert_frame_equal(first.loc[first["split"] == "validation", columns],
                                  second.loc[second["split"] == "validation", columns])
    assert windows["test"]["training_end"] == "2020-02-04"
    assert windows["test"]["evaluation_start"] == "2020-02-05"
    # Mutating test observations alone cannot alter test forecasts either.
    test_only = original.copy()
    test_only.loc[test_only["date"] >= pd.Timestamp("2020-02-05"), "units"] = 9000
    third, _, _ = evaluate_baselines(test_only, source_run_id="test", validation_days=7, test_days=7)
    pd.testing.assert_frame_equal(first[columns], third[columns])


def test_segmentation_and_reproducibility(sources):
    first, metrics, _ = evaluate_baselines(panel(sources), source_run_id="test", validation_days=7, test_days=7)
    second, _, _ = evaluate_baselines(panel(sources), source_run_id="test", validation_days=7, test_days=7)
    pd.testing.assert_frame_equal(first, second)
    assert set(metrics["segment_type"]) == {"overall", "store", "department", "demand_level", "horizon"}
    assert set(first["split"]) == {"validation", "test"}
    assert metrics.loc[metrics["segment_type"] == "overall", "observations"].eq(42).all()
    assert set(metrics["model"]) == {"last_value", "rolling_mean", "seasonal_naive_7"}


def test_segment_wmape_uses_ratio_of_totals():
    rows = pd.DataFrame({"split": ["test", "test"], "model": ["last_value"]*2,
                         "store_id": ["a", "b"], "dept_id": ["d", "d"],
                         "demand_level": ["low", "high"], "horizon": [1, 1],
                         "actual_units": [1, 100], "predicted_units": [0, 100],
                         "source_run_id": ["test"]*2})
    overall = segmented_metrics(rows).query("segment_type == 'overall'").iloc[0]
    assert overall["WMAPE"] == pytest.approx(1 / 101)


def test_insufficient_history_gaps_duplicates_rejected(sources):
    frame = panel(sources)
    with pytest.raises(QualityError, match="Insufficient history"):
        temporal_split(frame)
    with pytest.raises(QualityError, match="complete common daily history"):
        validate_panel(frame.drop(index=12))
    with pytest.raises(QualityError, match="duplicate key"):
        validate_panel(pd.concat([frame, frame.iloc[:1]]))
    with pytest.raises(QualityError, match="Insufficient baseline"):
        predict_baselines(frame.loc[frame["date"] < "2020-01-07"], 1, split="test", source_run_id="test")
