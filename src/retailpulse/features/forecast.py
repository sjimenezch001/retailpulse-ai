"""Compact daily panels and strictly past-only features for recursive forecasts."""
from dataclasses import dataclass

import numpy as np
import pandas as pd

from retailpulse.quality.checks import require, unique

IDENTITY = ["store_id", "item_id", "dept_id", "cat_id", "state_id"]
CALENDAR = ["day_of_week", "day_of_month", "week_of_year", "month", "year", "weekend"]
LAGS = [1, 7, 14, 28]
CORE = IDENTITY + CALENDAR + [f"lag_{lag}" for lag in LAGS]
EXTRA = ["rolling_mean_7", "rolling_mean_14", "rolling_mean_28",
         "rolling_std_7", "rolling_std_28", "sell_price_lag_1",
         "price_missing_lag_1", "price_change_pct_lag_1", "event_1", "event_2", "snap"]
FEATURE_VERSION = "past-only-recursive-v1"


@dataclass
class Panel:
    dates: pd.DatetimeIndex
    series: pd.DataFrame
    units: np.ndarray
    prices: np.ndarray
    calendar: pd.DataFrame


def calendar_input(db, start, end) -> pd.DataFrame:
    """Calendar schedules are known in advance; no observed sales or prices."""
    names = {row[0] for row in db.execute("DESCRIBE dim_calendar").fetchall()}
    optional = [f'"{name}"' if name in names else f'NULL AS "{name}"'
                for name in ["event_name_1", "event_name_2", "snap_CA", "snap_TX", "snap_WI"]]
    frame = db.execute(f"SELECT date, {', '.join(optional)} FROM dim_calendar "
                       "WHERE date BETWEEN ? AND ? ORDER BY date", [start, end]).fetchdf()
    unique(frame, ["date"], "forecast calendar")
    return frame.set_index("date")


def load_panel(db, origin, training_days=730) -> Panel:
    """Read a bounded history only. Never fetch units or prices beyond origin."""
    require(training_days > 0, "Training window must be positive")
    origin = pd.Timestamp(origin)
    start = origin - pd.Timedelta(days=training_days + 27)
    series = db.execute("SELECT DISTINCT store_id, item_id, dept_id, cat_id, state_id "
                        "FROM mart_sales_daily WHERE date = ? ORDER BY store_id, item_id",
                        [origin]).fetchdf()
    require(not series.empty, "No series at forecast origin")
    unique(series, ["store_id", "item_id"], "model series")
    require(not series[IDENTITY].isna().any().any(), "Null model identity")
    codes = series[["store_id", "item_id"]].assign(series_code=np.arange(len(series), dtype="int32"))
    db.register("model_series_codes", codes)
    try:
        data = db.execute(
            "SELECT s.date, c.series_code, s.units::FLOAT AS units, "
            "s.sell_price::FLOAT AS sell_price FROM mart_sales_daily s "
            "JOIN model_series_codes c USING (store_id, item_id) "
            "WHERE s.date BETWEEN ? AND ? ORDER BY s.date, c.series_code", [start, origin]
        ).fetchdf()
    finally:
        db.unregister("model_series_codes")
    dates = pd.date_range(data["date"].min(), origin)
    n = len(series)
    require(len(dates) > 28, "At least 29 historical days are needed for model training")
    require(len(data) == len(dates) * n, "Incomplete model panel")
    require(np.array_equal(data["series_code"].to_numpy(), np.tile(np.arange(n), len(dates)))
            and np.array_equal(data["date"].to_numpy(), np.repeat(dates.to_numpy(), n)),
            "Model panel must be unique and complete")
    units = data["units"].to_numpy(dtype="float32").reshape(-1, n).copy()
    prices = data["sell_price"].to_numpy(dtype="float32").reshape(-1, n).copy()
    require(bool(np.isfinite(units).all() and (units >= 0).all()), "Invalid model targets")
    require(bool((np.isnan(prices) | (np.isfinite(prices) & (prices > 0))).all()),
            "Invalid model prices")
    return Panel(dates, series, units, prices, calendar_input(db, dates[0], origin))


def categories_for(series: pd.DataFrame) -> dict:
    return {name: sorted(series[name].unique().tolist()) for name in IDENTITY}


def date_features(dates, series, calendar, categories) -> dict:
    """Day-major order, with categorical domains learned at the training origin."""
    dates = pd.DatetimeIndex(dates)
    n = len(series)
    result = {}
    for name in IDENTITY:
        encoded = pd.Categorical(series[name], categories=categories[name])
        require(bool((encoded.codes >= 0).all()), "Unseen forecast series category")
        result[name] = pd.Categorical.from_codes(np.tile(encoded.codes, len(dates)),
                                                categories=categories[name])
    for name, values in zip(CALENDAR, [dates.dayofweek, dates.day, dates.isocalendar().week,
                                       dates.month, dates.year, dates.dayofweek >= 5], strict=True):
        result[name] = np.repeat(np.asarray(values, dtype="int32"), n)
    require(dates.isin(calendar.index).all(), "Missing forecast calendar dates")
    cal = calendar.loc[dates]
    for i in (1, 2):
        event = cal[f"event_name_{i}"].fillna("").ne("").to_numpy(dtype="int32")
        result[f"event_{i}"] = np.repeat(event, n)
    snap = np.zeros((len(dates), n), dtype="int32")
    for state in ("CA", "TX", "WI"):
        mask = series["state_id"].eq(state).to_numpy()
        snap[:, mask] = cal[f"snap_{state}"].fillna(0).to_numpy(dtype="int32")[:, None]
    result["snap"] = snap.ravel()
    return result


def price_features(previous, before_previous) -> dict:
    change = np.full(previous.shape, np.nan, dtype="float32")
    valid = np.isfinite(previous) & np.isfinite(before_previous) & (before_previous > 0)
    change[valid] = 100 * (previous[valid] - before_previous[valid]) / before_previous[valid]
    return {"sell_price_lag_1": previous.ravel(),
            "price_missing_lag_1": np.isnan(previous).astype("int32").ravel(),
            "price_change_pct_lag_1": change.ravel()}


def training_features(panel: Panel, feature_set: str, categories=None):
    """All target-day histories end at t-1, including prices and rolling moments."""
    require(feature_set in ("core", "extended"), "Unknown feature set")
    categories = categories or categories_for(panel.series)
    dates, values = panel.dates[28:], panel.units
    require(len(dates) > 0, "Empty training matrix after lag warmup")
    data = date_features(dates, panel.series, panel.calendar, categories)
    for lag in LAGS:
        data[f"lag_{lag}"] = values[28-lag:len(values)-lag].ravel()
    # Float64 accumulators avoid cancellation; retained model features are float32.
    sums = np.vstack([np.zeros((1, values.shape[1])), np.cumsum(values, axis=0, dtype="float64")])
    squares = np.vstack([np.zeros((1, values.shape[1])),
                         np.cumsum(np.square(values, dtype="float64"), axis=0)])
    for window in (7, 14, 28):
        means = (sums[28:-1] - sums[28-window:-1-window]) / window
        data[f"rolling_mean_{window}"] = means.astype("float32").ravel()
        if window != 14:
            variance = (squares[28:-1] - squares[28-window:-1-window]) / window - means**2
            data[f"rolling_std_{window}"] = np.sqrt(np.maximum(variance, 0)).astype("float32").ravel()
    data.update(price_features(panel.prices[27:-1], panel.prices[26:-2]))
    names = CORE if feature_set == "core" else CORE + EXTRA
    return pd.DataFrame({name: data[name] for name in names}), values[28:].ravel(), categories


def recursive_predict(model, panel: Panel, calendar, horizon, feature_set, categories):
    """Append predictions only; the API has no held-out actual-unit argument."""
    require(horizon > 0, "Forecast horizon must be positive")
    history = panel.units[-28:].copy()
    previous_price, before_price = panel.prices[-1].copy(), panel.prices[-2].copy()
    names = CORE if feature_set == "core" else CORE + EXTRA
    predictions = []
    for step in range(1, horizon + 1):
        date = panel.dates[-1] + pd.Timedelta(days=step)
        data = date_features([date], panel.series, calendar, categories)
        for lag in LAGS:
            data[f"lag_{lag}"] = history[-lag]
        for window in (7, 14, 28):
            data[f"rolling_mean_{window}"] = history[-window:].mean(axis=0, dtype="float64").astype("float32")
            if window != 14:
                data[f"rolling_std_{window}"] = history[-window:].std(axis=0, dtype="float64").astype("float32")
        data.update(price_features(previous_price, before_price))
        features = pd.DataFrame({name: data[name] for name in names})
        predicted = np.maximum(model.predict(features, num_threads=4), 0)
        require(bool(np.isfinite(predicted).all()), "Non-finite model prediction")
        predictions.append(predicted)
        history = np.vstack([history[1:], predicted.astype("float32")])
        # Future prices are unknown: carry the origin price, never query held-out prices.
        before_price = previous_price
    return np.asarray(predictions)
