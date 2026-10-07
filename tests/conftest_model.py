"""Generated synthetic model panels; no competition observations are embedded."""
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pytest

from retailpulse.features.forecast import Panel
from retailpulse.models.candidate import BASE_PARAMS


@pytest.fixture
def model_panel():
    dates = pd.date_range("2020-01-01", periods=140)
    series = pd.DataFrame({"store_id": ["SYN_A", "SYN_A", "SYN_B", "SYN_B"],
                           "item_id": ["SYN_1", "SYN_2", "SYN_1", "SYN_2"],
                           "dept_id": ["SYN_D1", "SYN_D2"] * 2,
                           "cat_id": ["SYN_CAT"] * 4, "state_id": ["CA"] * 4})
    units = ((np.arange(140)[:, None] % 7) + np.arange(4)[None, :]).astype("float32")
    prices = np.broadcast_to(1 + np.arange(140)[:, None] / 100, (140, 4)).astype("float32").copy()
    prices[:3] = np.nan
    calendar = pd.DataFrame({"event_name_1": ["Synthetic event" if i % 13 == 0 else "" for i in range(140)],
                             "event_name_2": "", "snap_CA": np.arange(140) % 2,
                             "snap_TX": 0, "snap_WI": 0}, index=dates)
    return Panel(dates, series, units, prices, calendar)


@pytest.fixture
def tiny_candidates():
    return [{"name": "synthetic_core", "feature_set": "core", "rounds": 8,
             "params": {**BASE_PARAMS, "num_threads": 1, "num_leaves": 7, "min_data_in_leaf": 3}},
            {"name": "synthetic_extended", "feature_set": "extended", "rounds": 8,
             "params": {**BASE_PARAMS, "num_threads": 1, "num_leaves": 7, "min_data_in_leaf": 3}}]


@pytest.fixture
def model_gold(model_panel, tmp_path):
    panel = model_panel
    output = tmp_path / "data/processed"
    (output / "gold").mkdir(parents=True)
    frame = pd.DataFrame({"date": np.repeat(panel.dates, 4),
                          **{name: np.tile(panel.series[name], len(panel.dates)) for name in panel.series},
                          "units": panel.units.ravel().astype("int32"), "sell_price": panel.prices.ravel(),
                          "rolling_28d": 0., "demand_spike_flag": False, "price_change_pct": 0.,
                          "pipeline_run_id": "synthetic-silver"})
    calendar = panel.calendar.rename_axis("date").reset_index()
    with duckdb.connect(str(output / "gold/retailpulse.duckdb")) as db:
        db.register("synthetic_sales", frame)
        db.register("synthetic_calendar", calendar)
        db.execute("CREATE TABLE mart_sales_daily AS SELECT * FROM synthetic_sales")
        db.execute("CREATE TABLE dim_calendar AS SELECT * FROM synthetic_calendar")
        db.execute("CREATE TABLE pipeline_metadata AS SELECT 'synthetic-model-gold' AS gold_run_id, "
                   "max(date) AS last_sales_date FROM mart_sales_daily")
        sql = Path(__file__).resolve().parents[1] / "sql/gold/interfaces.sql"
        db.execute(sql.read_text(encoding="utf-8"))
    return output
