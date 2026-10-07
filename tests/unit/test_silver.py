import pandas as pd
import pytest

from retailpulse.quality.checks import QualityError
from retailpulse.transforms.silver import build_silver

STORES = ["SYN_A", "SYN_B", "SYN_C"]
DEPARTMENTS = ["SYN_D1", "SYN_D2"]


def build(sources):
    return build_silver(sources, STORES, DEPARTMENTS)


def test_grain_dates_totals_dimensions_and_missing_prices(sources):
    tables = build(sources)
    fact = tables["fact_sales_daily"]
    assert len(fact) == 6 * 42
    assert not fact.duplicated(["date", "store_id", "item_id"]).any()
    assert pd.api.types.is_datetime64_any_dtype(fact["date"])
    assert fact["units"].sum() == sum(sources["sales"][f"d_{i}"].sum() for i in range(1, 43))
    assert fact["price_missing"].sum() == 7
    assert fact.loc[fact["price_missing"], "sell_price"].isna().all()
    assert set(fact["item_id"]) == set(tables["dim_product"]["item_id"])
    assert set(fact["store_id"]) == set(tables["dim_store"]["store_id"])
    assert len(tables["dim_product"]) == 2
    assert len(tables["dim_store"]) == 3
    pd.testing.assert_frame_equal(fact, build(sources)["fact_sales_daily"])


@pytest.mark.parametrize("table", ["sales", "calendar", "prices"])
def test_duplicate_keys_fail(sources, table):
    sources[table] = pd.concat([sources[table], sources[table].iloc[:1]])
    with pytest.raises(QualityError, match="duplicate key"):
        build(sources)


@pytest.mark.parametrize("value", [-1, 0.5, float("nan"), float("inf")])
def test_invalid_units_fail(sources, value):
    sources["sales"]["d_1"] = sources["sales"]["d_1"].astype(float)
    sources["sales"].loc[0, "d_1"] = value
    with pytest.raises(QualityError, match="units"):
        build(sources)


def test_missing_calendar_day_fails(sources):
    sources["calendar"] = sources["calendar"].iloc[1:]
    with pytest.raises(QualityError, match="missing from calendar"):
        build(sources)


def test_invalid_date_fails(sources):
    sources["calendar"].loc[0, "date"] = "bad"
    with pytest.raises(QualityError, match="invalid date"):
        build(sources)


def test_conflicting_product_mapping_fails(sources):
    sources["sales"]["dept_id"] = sources["sales"]["dept_id"].astype("str")
    sources["sales"].loc[0, "dept_id"] = "WRONG"
    with pytest.raises(QualityError, match="product mapping"):
        build(sources)


def test_unknown_price_series_fails(sources):
    sources["prices"]["item_id"] = sources["prices"]["item_id"].astype("str")
    sources["prices"].loc[0, "item_id"] = "UNKNOWN"
    with pytest.raises(QualityError, match="unknown sales series"):
        build(sources)


def test_empty_and_unknown_pilot_fail(sources):
    with pytest.raises(QualityError, match="empty"):
        build_silver(sources, [], [])
    with pytest.raises(QualityError, match="Unknown pilot store"):
        build_silver(sources, ["UNKNOWN"], DEPARTMENTS)


def test_negative_price_fails(sources):
    sources["prices"].loc[0, "sell_price"] = -1.0
    with pytest.raises(QualityError, match="sell_price"):
        build(sources)
