"""Forecast errors with an explicit undefined WMAPE for all-zero actuals."""
from math import sqrt

import pandas as pd

from retailpulse.quality.checks import numeric, require


def forecast_metrics(actual, predicted) -> dict:
    actual = pd.Series(actual, dtype="float64").reset_index(drop=True)
    predicted = pd.Series(predicted, dtype="float64").reset_index(drop=True)
    require(len(actual) == len(predicted) and len(actual) > 0, "Metrics require aligned nonempty arrays")
    actual = numeric(actual, "actual units")
    predicted = numeric(predicted, "predicted units")
    errors = (actual - predicted).abs()
    denominator = float(actual.abs().sum())
    return {"observations": len(actual),
            "WMAPE": float(errors.sum()) / denominator if denominator else None,
            "MAE": float(errors.mean()), "RMSE": sqrt(float((errors ** 2).mean())),
            "wmape_zero_denominator": denominator == 0}


def segmented_metrics(predictions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    segments = {"overall": None, "store": "store_id", "department": "dept_id",
                "demand_level": "demand_level", "horizon": "horizon"}
    for (split, model), block in predictions.groupby(["split", "model"], observed=True, sort=True):
        for segment_type, column in segments.items():
            groups = [("all", block)] if column is None else block.groupby(column, observed=True, sort=True)
            for segment, group in groups:
                rows.append({"split": split, "model": model, "segment_type": segment_type,
                             "segment": str(segment),
                             **forecast_metrics(group["actual_units"], group["predicted_units"]),
                             "source_run_id": group["source_run_id"].iloc[0]})
    return pd.DataFrame(rows)
