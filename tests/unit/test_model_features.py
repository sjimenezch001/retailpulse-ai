from dataclasses import replace

import lightgbm as lgb
import numpy as np
import pandas as pd
import pytest

from retailpulse.features.forecast import recursive_predict, training_features
from retailpulse.models.candidate import (
    fit_candidate,
    predict_candidate,
    select_candidate,
    temporal_windows,
)
from retailpulse.models.metrics import forecast_metrics
from retailpulse.quality.checks import QualityError


def test_lags_rolling_and_prices_exclude_target_and_future(model_panel):
    original, target, _ = training_features(model_panel, "extended")
    changed_units, changed_prices = model_panel.units.copy(), model_panel.prices.copy()
    changed_units[60:] = 9999
    changed_prices[60:] = 9999
    changed, _, _ = training_features(replace(model_panel, units=changed_units, prices=changed_prices), "extended")
    through_target = (60 - 28 + 1) * 4
    pd.testing.assert_frame_equal(original.iloc[:through_target], changed.iloc[:through_target])
    row = original.iloc[(60 - 28) * 4]
    for lag in (1, 7, 14, 28):
        assert row[f"lag_{lag}"] == model_panel.units[60 - lag, 0]
    for window in (7, 14, 28):
        assert row[f"rolling_mean_{window}"] == pytest.approx(model_panel.units[60-window:60, 0].mean())
        if window != 14:
            assert row[f"rolling_std_{window}"] == pytest.approx(model_panel.units[60-window:60, 0].std())
    assert row["sell_price_lag_1"] == model_panel.prices[59, 0]
    assert target[(60 - 28) * 4] == model_panel.units[60, 0]
    assert all(original[name].dtype == "float32" for name in original if name.startswith(("lag_", "rolling_")))


def test_recursive_forecasts_feed_predictions_and_hold_origin_price(model_panel):
    history = replace(model_panel, dates=model_panel.dates[:80], units=model_panel.units[:80],
                      prices=model_panel.prices[:80])
    seen = []

    class Recorder:
        def predict(self, features, **_):
            seen.append(features.copy())
            return np.full(len(features), 42.)

    _, _, categories = training_features(history, "extended")
    recursive_predict(Recorder(), history, model_panel.calendar, 28, "extended", categories)
    assert seen[1]["lag_1"].eq(42).all()
    assert seen[7]["lag_7"].eq(42).all()
    assert seen[-1]["rolling_mean_7"].eq(42).all()
    np.testing.assert_array_equal(seen[-1]["sell_price_lag_1"], model_panel.prices[79])
    assert seen[-1]["price_change_pct_lag_1"].eq(0).all()


def test_fixed_seed_predictions_and_native_model_roundtrip(model_panel, tiny_candidates, tmp_path):
    history = replace(model_panel, dates=model_panel.dates[:80], units=model_panel.units[:80],
                      prices=model_panel.prices[:80])
    first, categories, _ = fit_candidate(history, tiny_candidates[1])
    second, _, _ = fit_candidate(history, tiny_candidates[1])
    path = tmp_path / "model.txt"
    first.save_model(str(path))
    loaded = lgb.Booster(model_file=str(path))
    predictions = [recursive_predict(model, history, model_panel.calendar, 28, "extended", categories)
                   for model in (first, second, loaded)]
    np.testing.assert_array_equal(predictions[0], predictions[1])
    np.testing.assert_array_equal(predictions[0], predictions[2])


def test_rp06_temporal_boundaries():
    windows = temporal_windows("2016-05-22")
    assert windows["validation"] == {"origin": "2016-03-27", "start": "2016-03-28",
                                     "end": "2016-04-24", "days": 28}
    assert windows["test"] == {"origin": "2016-04-24", "start": "2016-04-25",
                               "end": "2016-05-22", "days": 28}
    with pytest.raises(QualityError):
        temporal_windows("2016-05-22", test_days=0)


def test_selection_accepts_validation_only_and_ignores_test_diagnostics():
    a = {"configuration": {"name": "A"}, "split": "validation", "metrics": {"WMAPE": .5},
         "test_metrics": {"WMAPE": .01}}
    b = {"configuration": {"name": "B"}, "split": "validation", "metrics": {"WMAPE": .4},
         "test_metrics": {"WMAPE": 99}}
    assert select_candidate([a, b]) is b
    with pytest.raises(QualityError, match="validation metrics only"):
        select_candidate([a, {**b, "split": "test"}])
    with pytest.raises(QualityError, match="undefined"):
        select_candidate([{**a, "metrics": {"WMAPE": None}}])


def test_candidate_metrics_match_manual_calculation():
    result = forecast_metrics([0, 2, 8], [1, 2, 5])
    assert result["WMAPE"] == pytest.approx(.4)
    assert result["MAE"] == pytest.approx(4 / 3)
    assert result["RMSE"] == pytest.approx(np.sqrt(10 / 3))


def test_training_cannot_cross_forecast_origin(model_panel, tiny_candidates):
    with pytest.raises(QualityError, match="Training must end at forecast origin"):
        predict_candidate(None, None, model_panel, model_panel.calendar,
                          {"origin": "2020-03-01"}, tiny_candidates[0], {}, "validation", "synthetic")
