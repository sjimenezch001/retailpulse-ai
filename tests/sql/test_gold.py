from datetime import date
from pathlib import Path

import duckdb
import pandas as pd
import pytest

from retailpulse.ingestion.bronze import ingest
from retailpulse.quality.checks import QualityError
from retailpulse.transforms.gold import build_gold, run_gold
from retailpulse.transforms.silver import build_silver, run_silver

SQL = Path(__file__).resolve().parents[2] / "sql"
STORES, DEPARTMENTS = ["SYN_A", "SYN_B", "SYN_C"], ["SYN_D1", "SYN_D2"]


def gold_tables(sources):
    sources["sales"] = sources["sales"].assign(pipeline_run_id="synthetic-test-run", ingestion_ts="2020-02-12T00:00:00+00:00")
    return build_silver(sources, STORES, DEPARTMENTS)


def test_metric_windows_price_nulls_and_totals(sources):
    tables = gold_tables(sources)
    with duckdb.connect() as db:
        build_gold(db, tables, SQL, date(2020, 2, 12))
        frame = db.execute("SELECT * FROM mart_sales_daily WHERE store_id='SYN_A' AND item_id='SYN_ITEM1' ORDER BY date").fetchdf()
        assert frame.loc[:6, "rolling_7d"].isna().all()
        assert frame.loc[7, "rolling_7d"] == pytest.approx(4.0)
        assert frame.loc[:27, "rolling_28d"].isna().all()
        assert frame.loc[28, "rolling_28d"] == pytest.approx(4.0)
        assert frame.loc[:6, "revenue_proxy"].isna().all()
        assert pd.isna(frame.loc[7, "price_change_pct"])
        assert frame.loc[14, "price_change_pct"] == pytest.approx(100 * (2.2 - 2.1) / 2.1)
        assert frame["data_freshness"].unique().tolist() == [1]
        assert db.execute("SELECT sum(units) FROM mart_store_weekly").fetchone()[0] == tables["fact_sales_daily"]["units"].sum()
        assert db.execute("SELECT revenue_proxy FROM mart_store_weekly WHERE store_id='SYN_A' AND dept_id='SYN_D1' AND wm_yr_wk=100").fetchone() == (None,)
        assert db.execute("SELECT count(*) FROM metric_definitions").fetchone() == (7,)
        assert db.execute("SELECT count(*) FROM fact_forecast").fetchone() == (0,)


def test_spike_rule_and_no_future_leakage(sources):
    base = gold_tables(sources)
    altered = {k: v.copy() for k, v in base.items()}
    fact = altered["fact_sales_daily"]
    key = (fact["store_id"] == "SYN_A") & (fact["item_id"] == "SYN_ITEM1")
    cutoff = pd.Timestamp("2020-02-05")
    fact.loc[key & (fact["date"] >= cutoff), "units"] = 1000
    with duckdb.connect() as original, duckdb.connect() as changed:
        build_gold(original, base, SQL, date(2020, 2, 12))
        build_gold(changed, altered, SQL, date(2020, 2, 12))
        query = "SELECT * FROM mart_sales_daily WHERE date < DATE '2020-02-05' ORDER BY date, store_id, item_id"
        pd.testing.assert_frame_equal(original.execute(query).fetchdf(), changed.execute(query).fetchdf())
        assert changed.execute("SELECT demand_spike_flag FROM mart_sales_daily WHERE store_id='SYN_A' AND item_id='SYN_ITEM1' AND date=DATE '2020-02-05'").fetchone() == (True,)


def test_gold_rejects_gaps_and_future_observations(sources):
    tables = gold_tables(sources)
    with duckdb.connect() as db, pytest.raises(QualityError, match="as_of"):
        build_gold(db, tables, SQL, date(2019, 1, 1))
    tables["fact_sales_daily"] = tables["fact_sales_daily"].drop(index=12)
    with duckdb.connect() as db, pytest.raises(QualityError, match="complete daily"):
        build_gold(db, tables, SQL, date(2020, 2, 12))


def test_pipeline_reconciliation_queries_and_idempotency(fixture_dir, tmp_path):
    bronze = ingest(fixture_dir, tmp_path / "bronze")
    silver = run_silver(tmp_path, STORES, DEPARTMENTS)
    first = run_gold(tmp_path, SQL, date(2020, 2, 12))
    second = run_gold(tmp_path, SQL, date(2020, 2, 12))
    assert second["reused"]
    assert first["gold_run_id"] == second["gold_run_id"]
    with duckdb.connect(str(tmp_path / "gold/retailpulse.duckdb"), read_only=True) as db:
        assert db.execute("SELECT sum(units) FROM mart_sales_daily").fetchone()[0] == silver["metrics"]["units"]
        assert db.execute("SELECT bronze_run_id FROM pipeline_metadata").fetchone()[0] == bronze["pipeline_run_id"]
        for query in sorted((SQL / "queries").glob("*.sql")):
            result = db.execute(query.read_text(encoding="utf-8")).fetchdf()
            if query.name.startswith("03"):
                assert result.empty
            else:
                assert not result.empty
        assert not db.execute((SQL / "checks/gold_quality.sql").read_text()).fetchall()
    assert run_gold(tmp_path, SQL, date(2020, 2, 13))["gold_run_id"] != first["gold_run_id"]


def test_sql_quality_check_detects_tampering(sources):
    with duckdb.connect() as db:
        build_gold(db, gold_tables(sources), SQL, date(2020, 2, 12))
        db.execute("UPDATE mart_sales_daily SET units=-1 WHERE store_id='SYN_A'")
        failures = db.execute((SQL / "checks/gold_quality.sql").read_text()).fetchall()
        assert ("negative_or_null_units",) in failures
        assert ("silver_gold_units_mismatch",) in failures
