"""Predeclared LightGBM candidates and validation-only model selection."""
import gc
from time import perf_counter

import lightgbm as lgb
import numpy as np
import pandas as pd

from retailpulse.features.forecast import recursive_predict, training_features
from retailpulse.models.baseline import demand_level
from retailpulse.quality.checks import require

MODEL_NAME = "lightgbm_global_v1"
BASE_PARAMS = {"objective": "poisson", "learning_rate": 0.05, "num_leaves": 31,
               "min_data_in_leaf": 100, "max_bin": 127, "num_threads": 4,
               "histogram_pool_size": 128, "seed": 2026, "data_random_seed": 2026,
               "feature_fraction_seed": 2026, "bagging_seed": 2026,
               "deterministic": True, "force_col_wise": True, "verbosity": -1}
CANDIDATES = [
    {"name": "A_core_poisson", "feature_set": "core", "rounds": 200, "params": BASE_PARAMS.copy()},
    {"name": "B_extended_poisson", "feature_set": "extended", "rounds": 200, "params": BASE_PARAMS.copy()},
    {"name": "C_extended_l1", "feature_set": "extended", "rounds": 200,
     "params": {**BASE_PARAMS, "objective": "regression_l1"}},
]


def temporal_windows(last_date, validation_days=28, test_days=28) -> dict:
    require(validation_days > 0 and test_days > 0, "Holdout windows must be positive")
    end = pd.Timestamp(last_date).normalize()
    test_origin = end - pd.Timedelta(days=test_days)
    validation_origin = test_origin - pd.Timedelta(days=validation_days)
    return {split: {"origin": origin.date().isoformat(),
                    "start": (origin + pd.Timedelta(days=1)).date().isoformat(),
                    "end": (origin + pd.Timedelta(days=days)).date().isoformat(),
                    "days": days}
            for split, origin, days in [("validation", validation_origin, validation_days),
                                         ("test", test_origin, test_days)]}


def fit_candidate(panel, configuration):
    started = perf_counter()
    features, target, categories = training_features(panel, configuration["feature_set"])
    names = features.columns.tolist()
    dataset = lgb.Dataset(features, label=target, categorical_feature="auto", free_raw_data=True)
    fit_started = perf_counter()
    model = lgb.train(configuration["params"], dataset, num_boost_round=configuration["rounds"])
    fit_seconds = perf_counter() - fit_started
    details = {"features": names, "training_rows": len(target),
               "training_start": panel.dates[28].date().isoformat(),
               "training_end": panel.dates[-1].date().isoformat(),
               "history_start": panel.dates[0].date().isoformat(),
               "fit_seconds": fit_seconds, "training_seconds": perf_counter() - started}
    del dataset, features, target
    gc.collect()
    return model, categories, details


def predict_candidate(db, model, panel, calendar, window, configuration, categories,
                      split, source_run_id):
    require(panel.dates[-1] == pd.Timestamp(window["origin"]), "Training must end at forecast origin")
    dates = pd.date_range(window["start"], window["end"])
    require(len(dates) == window["days"] and dates[0] > panel.dates[-1],
            "Training must precede every forecast target")
    values = recursive_predict(model, panel, calendar, len(dates),
                               configuration["feature_set"], categories)
    # Match RP-06 demand segments using ALL observed history through this origin.
    levels = db.execute("SELECT store_id, item_id, avg(units) AS mean_units "
                        "FROM mart_sales_daily WHERE date <= ? GROUP BY store_id, item_id",
                        [pd.Timestamp(window["origin"])]).fetchdf()
    series = panel.series.merge(levels, on=["store_id", "item_id"], validate="one_to_one", how="left")
    require(not series["mean_units"].isna().any(), "Missing historical demand segment")
    n = len(series)
    result = pd.DataFrame({"forecast_origin": panel.dates[-1], "target_date": np.repeat(dates, n),
                           **{name: np.tile(series[name], len(dates))
                              for name in ["store_id", "item_id", "dept_id"]},
                           "model": MODEL_NAME, "split": split,
                           "horizon": np.repeat(np.arange(1, len(dates) + 1), n),
                           "predicted_units": values.ravel(),
                           "demand_level": np.tile(series["mean_units"].map(demand_level), len(dates)),
                           "training_start": panel.dates[28], "training_end": panel.dates[-1],
                           "source_run_id": source_run_id})
    return result


def attach_actuals(db, forecasts):
    """Called only AFTER predictions; workflow guards the single test invocation."""
    actual = db.execute("SELECT date AS target_date, store_id, item_id, units AS actual_units "
                        "FROM mart_sales_daily WHERE date BETWEEN ? AND ?",
                        [forecasts["target_date"].min(), forecasts["target_date"].max()]).fetchdf()
    result = forecasts.merge(actual, on=["target_date", "store_id", "item_id"],
                             how="left", validate="one_to_one")
    require(not result["actual_units"].isna().any(), "Missing held-out observations")
    return result


def select_candidate(results):
    require(bool(results) and all(result["split"] == "validation" for result in results),
            "Candidate selection accepts validation metrics only")
    eligible = [result for result in results if result["metrics"]["WMAPE"] is not None
                and np.isfinite(result["metrics"]["WMAPE"])]
    require(bool(eligible), "Validation WMAPE is undefined for all candidates")
    return min(eligible, key=lambda result: (result["metrics"]["WMAPE"], result["configuration"]["name"]))
