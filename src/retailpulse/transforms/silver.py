"""M5 wide sales to validated daily entities, preserving missing prices."""
from pathlib import Path

import pandas as pd

from retailpulse.data.snapshots import publish_tables
from retailpulse.data.source import day_columns, schema_problems
from retailpulse.ingestion.bronze import read_bronze
from retailpulse.quality.checks import numeric, require, unique

SILVER_VERSION = "silver-v1"


def build_silver(frames: dict[str, pd.DataFrame], stores: list[str],
                 departments: list[str]) -> dict[str, pd.DataFrame]:
    require(bool(stores) and bool(departments), "Pilot selections are empty")
    for name, frame in frames.items():
        require(not schema_problems(name, frame), f"Invalid {name} schema")
    sales, calendar, prices = (frames[k].copy() for k in ("sales", "calendar", "prices"))
    # Remove categorical grouping surprises and unused pilot identifier categories.
    for frame in (sales, calendar, prices):
        for column in frame.select_dtypes("category"):
            frame[column] = frame[column].astype("str")
    unique(sales, ["id"], "sales id")
    unique(sales, ["store_id", "item_id"], "sales series")
    unique(calendar, ["d"], "calendar day")
    dates = pd.to_datetime(calendar["date"], format="%Y-%m-%d", errors="coerce")
    require(not dates.isna().any(), "calendar: invalid date")
    calendar["date"] = dates
    unique(calendar, ["date"], "calendar date")
    calendar["wm_yr_wk"] = numeric(calendar["wm_yr_wk"], "calendar week", positive=True, integral=True)
    unique(prices, ["store_id", "item_id", "wm_yr_wk"], "prices")
    prices["wm_yr_wk"] = numeric(prices["wm_yr_wk"], "price week", positive=True, integral=True)
    prices["sell_price"] = numeric(prices["sell_price"], "sell_price", positive=True)
    products = sales[["item_id", "dept_id", "cat_id"]].drop_duplicates()
    locations = sales[["store_id", "state_id"]].drop_duplicates()
    unique(products, ["item_id"], "product mapping")
    unique(locations, ["store_id"], "store mapping")
    require(set(stores) <= set(sales["store_id"]), "Unknown pilot store")
    require(set(departments) <= set(sales["dept_id"]), "Unknown pilot department")
    pairs = sales[["store_id", "item_id"]]
    price_pairs = prices[["store_id", "item_id"]].drop_duplicates()
    require(len(price_pairs.merge(pairs, on=["store_id", "item_id"])) == len(price_pairs),
            "Price refers to unknown sales series")
    require(set(prices["wm_yr_wk"]) <= set(calendar["wm_yr_wk"]),
            "Price refers to unknown calendar week")
    days = day_columns(sales)
    numbers = [int(day[2:]) for day in days]
    require(numbers == list(range(numbers[0], numbers[-1] + 1)), "Noncontiguous sales day columns")
    require(set(days) <= set(calendar["d"]), "Sales day missing from calendar")
    observed_dates = calendar.set_index("d").loc[days, "date"]
    require(bool((observed_dates.diff().dropna() == pd.Timedelta(days=1)).all()),
            "Sales days must map to consecutive calendar dates")
    selected = sales.loc[sales["store_id"].isin(stores) & sales["dept_id"].isin(departments)].copy()
    require(not selected.empty, "Pilot contains no sales")
    combinations = selected[["store_id", "dept_id"]].drop_duplicates()
    require(len(combinations) == len(set(stores)) * len(set(departments)),
            "Pilot has missing store/department combinations")
    ids = ["item_id", "store_id", "dept_id", "cat_id", "state_id"]
    lineage = [c for c in ("pipeline_run_id", "ingestion_ts", "source_checksum") if c in selected]
    fact = selected.melt(id_vars=ids + lineage, value_vars=days, var_name="d", value_name="units")
    fact["units"] = numeric(fact["units"], "units", integral=True).astype("int64")
    fact = fact.merge(calendar[["d", "date", "wm_yr_wk"]], on="d", how="left", validate="many_to_one")
    fact = fact.merge(prices[["store_id", "item_id", "wm_yr_wk", "sell_price"]],
                      on=["store_id", "item_id", "wm_yr_wk"], how="left", validate="many_to_one")
    fact["price_missing"] = fact["sell_price"].isna()
    fact = fact.sort_values(["date", "store_id", "item_id"]).reset_index(drop=True)
    unique(fact, ["date", "store_id", "item_id"], "daily sales")
    require(len(fact) == len(selected) * len(days), "Silver row reconciliation failed")
    # Dimension lookups must not create or remove daily sales rows.
    dim_product = products.loc[products["item_id"].isin(selected["item_id"])].reset_index(drop=True)
    dim_store = locations.loc[locations["store_id"].isin(stores)].reset_index(drop=True)
    require(set(fact["item_id"]) <= set(dim_product["item_id"]), "Unknown fact product")
    require(set(fact["store_id"]) <= set(dim_store["store_id"]), "Unknown fact store")
    calendar = calendar.drop(columns=[c for c in ("source_file", "source_checksum", "pipeline_run_id", "ingestion_ts") if c in calendar])
    return {"fact_sales_daily": fact, "dim_calendar": calendar.sort_values("date").reset_index(drop=True),
            "dim_product": dim_product.sort_values("item_id").reset_index(drop=True),
            "dim_store": dim_store.sort_values("store_id").reset_index(drop=True)}


def run_silver(output: Path, stores: list[str], departments: list[str]) -> dict:
    frames, bronze = read_bronze(output / "bronze")
    tables = build_silver(frames, stores, departments)
    fact = tables["fact_sales_daily"]
    identity = {"version": SILVER_VERSION, "bronze_run_id": bronze["pipeline_run_id"],
                "stores": sorted(set(stores)), "departments": sorted(set(departments))}
    selected = frames["sales"].loc[frames["sales"]["store_id"].isin(stores)
                                   & frames["sales"]["dept_id"].isin(departments)]
    expected_units = int(selected[day_columns(selected)].to_numpy().sum())
    require(int(fact["units"].sum()) == expected_units, "Bronze to Silver units mismatch")
    return publish_tables(output / "silver", tables, identity, {
        "source_series": len(selected), "days": len(day_columns(selected)),
        "sales_rows": len(fact), "units": expected_units,
        "missing_price_rows": int(fact["price_missing"].sum()),
    })
