"""Fixed-origin baselines and chronological evaluation without future inputs."""
from pathlib import Path

import duckdb
import pandas as pd

from retailpulse.data.source import utc_now
from retailpulse.models.metrics import segmented_metrics
from retailpulse.quality.checks import numeric, require, unique

MODELS = ("last_value", "rolling_mean", "seasonal_naive_7")


def validate_panel(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame[["date", "store_id", "item_id", "dept_id", "units"]].copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    unique(frame, ["date", "store_id", "item_id"], "forecast panel")
    require(not frame.empty, "Empty forecast panel")
    require(not frame["dept_id"].isna().any(), "Null department in forecast panel")
    frame["units"] = numeric(frame["units"], "forecast units", integral=True)
    require(bool((frame["date"] == frame["date"].dt.normalize()).all()), "Forecast dates must be daily")
    groups = frame.groupby(["store_id", "item_id"], observed=True)
    sizes = groups["date"].agg(["min", "max", "count"])
    start, end = frame["date"].min(), frame["date"].max()
    require(bool(((sizes["min"] == start) & (sizes["max"] == end)
                  & (sizes["count"] == (end - start).days + 1)).all()),
            "Forecast panel must have complete common daily history")
    require(bool((groups["dept_id"].nunique() == 1).all()), "Conflicting forecast department")
    return frame.sort_values(["date", "store_id", "item_id"]).reset_index(drop=True)


def temporal_split(frame: pd.DataFrame, validation_days=28, test_days=28, min_train_days=28):
    require(validation_days > 0 and test_days > 0 and min_train_days > 0,
            "Temporal window sizes must be positive")
    frame = validate_panel(frame)
    dates = sorted(frame["date"].unique())
    require(len(dates) >= min_train_days + validation_days + test_days,
            "Insufficient history for temporal split")
    validation_start, test_start = dates[-validation_days - test_days], dates[-test_days]
    return {
        "train": frame.loc[frame["date"] < validation_start].copy(),
        "validation": frame.loc[(frame["date"] >= validation_start) & (frame["date"] < test_start)].copy(),
        "test": frame.loc[frame["date"] >= test_start].copy(),
    }


def demand_level(mean_units: float) -> str:
    if mean_units == 0:
        return "zero"
    if mean_units < 1:
        return "low"
    return "medium" if mean_units < 10 else "high"


def predict_baselines(training: pd.DataFrame, horizon: int, *, split: str,
                      source_run_id: str, rolling_window=7) -> pd.DataFrame:
    require(horizon > 0 and rolling_window > 0, "Horizon and rolling window must be positive")
    training = validate_panel(training)
    rows = []
    for (store, item), series in training.groupby(["store_id", "item_id"], observed=True, sort=True):
        series = series.sort_values("date")
        require(len(series) >= max(7, rolling_window), "Insufficient baseline training history")
        values = series["units"].tolist()
        origin = series["date"].iloc[-1]
        level = demand_level(float(series["units"].mean()))
        for model in MODELS:
            for step in range(1, horizon + 1):
                if model == "last_value":
                    prediction = float(values[-1])
                elif model == "rolling_mean":
                    prediction = float(series["units"].iloc[-rolling_window:].mean())
                else:
                    prediction = float(values[-7:][(step - 1) % 7])
                rows.append({
                    "forecast_origin": origin, "target_date": origin + pd.Timedelta(days=step),
                    "store_id": store, "item_id": item, "dept_id": series["dept_id"].iloc[0],
                    "model": model, "split": split, "horizon": step,
                    "predicted_units": prediction, "actual_units": float("nan"),
                    "demand_level": level, "training_start": series["date"].iloc[0],
                    "training_end": origin, "source_run_id": source_run_id,
                })
    return pd.DataFrame(rows)


def evaluate_baselines(frame: pd.DataFrame, *, source_run_id: str,
                       validation_days=28, test_days=28, rolling_window=7) -> tuple:
    parts = temporal_split(frame, validation_days, test_days, max(28, rolling_window))
    predictions, windows = [], {}
    for split in ("validation", "test"):
        history = parts["train"] if split == "validation" else pd.concat([parts["train"], parts["validation"]])
        actual = parts[split]
        horizon = actual["date"].nunique()
        forecast = predict_baselines(history, horizon, split=split,
                                     source_run_id=source_run_id, rolling_window=rolling_window)
        forecast = forecast.drop(columns="actual_units").merge(
            actual.rename(columns={"date": "target_date", "units": "actual_units"})[
                ["target_date", "store_id", "item_id", "actual_units"]],
            on=["target_date", "store_id", "item_id"], how="left", validate="many_to_one")
        require(not forecast["actual_units"].isna().any(), "Missing held-out observations")
        predictions.append(forecast)
        windows[split] = {
            "training_start": history["date"].min().date().isoformat(),
            "training_end": history["date"].max().date().isoformat(),
            "evaluation_start": actual["date"].min().date().isoformat(),
            "evaluation_end": actual["date"].max().date().isoformat(),
        }
    result = pd.concat(predictions, ignore_index=True)
    return result, segmented_metrics(result), windows


def run_baselines(output: Path, *, validation_days=28, test_days=28,
                  rolling_window=7, future_horizon=28) -> dict:
    path = output / "gold/retailpulse.duckdb"
    require(path.is_file(), "Gold database must exist before forecasting")
    with duckdb.connect(str(path)) as db:
        frame = db.execute("SELECT date, store_id, item_id, dept_id, units FROM mart_sales_daily").fetchdf()
        run_id = db.execute("SELECT gold_run_id FROM pipeline_metadata").fetchone()[0]
        predictions, metrics, windows = evaluate_baselines(
            frame, source_run_id=run_id, validation_days=validation_days,
            test_days=test_days, rolling_window=rolling_window)
        future = predict_baselines(frame, future_horizon, split="future", source_run_id=run_id,
                                   rolling_window=rolling_window)
        forecasts = pd.concat([predictions, future], ignore_index=True)
        import json

        run = pd.DataFrame([{
            "source_run_id": run_id, "generated_at": utc_now(),
            "validation_days": validation_days, "test_days": test_days,
            "rolling_window": rolling_window, "future_horizon": future_horizon,
            "windows_json": json.dumps(windows, sort_keys=True),
            "models": ",".join(MODELS), "baseline_version": "baseline-v1",
        }])
        db.register("forecast_input", forecasts)
        db.register("metrics_input", metrics)
        db.register("run_input", run)
        db.execute("BEGIN TRANSACTION")
        try:
            # Replace the active baseline run in one transaction; do not append duplicates.
            db.execute("DELETE FROM fact_forecast")
            db.execute("DELETE FROM forecast_evaluation")
            db.execute("INSERT INTO fact_forecast BY NAME SELECT * FROM forecast_input")
            db.execute("INSERT INTO forecast_evaluation BY NAME SELECT * FROM metrics_input")
            db.execute("CREATE OR REPLACE TABLE baseline_run AS SELECT * FROM run_input")
            db.execute("COMMIT")
        except Exception:
            db.execute("ROLLBACK")
            raise
    return {"source_run_id": run_id, "forecast_rows": len(forecasts),
            "evaluation_rows": len(metrics), "windows": windows,
            "models": list(MODELS), "future_horizon": future_horizon}
