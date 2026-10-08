"""BI contracts use generated synthetic Gold only; no M5 or Bronze required."""
import importlib.util
from pathlib import Path

import duckdb
import pytest

from retailpulse.bi.export import export_bi, prepare_views, validate_source

ROOT = Path(__file__).resolve().parents[1]
SQL = ROOT / "sql"


@pytest.fixture
def bi_gold(tmp_path):
    output = tmp_path / "processed"
    (output / "gold").mkdir(parents=True)
    with duckdb.connect(str(output / "gold/retailpulse.duckdb")) as db:
        db.execute("""
            CREATE TABLE dim_calendar AS SELECT date '2020-01-01'+i::INT AS date,
                2020 AS year,1 AS month,'Synthetic day' AS weekday,
                CASE WHEN i=3 THEN 'Synthetic event' END AS event_name_1,
                NULL::VARCHAR AS event_name_2,i%2 AS snap_CA,0 AS snap_TX,0 AS snap_WI
            FROM range(8) t(i);
            CREATE TABLE dim_store AS SELECT * FROM (VALUES ('SYN_A','CA'),('SYN_B','CA')) t(store_id,state_id);
            CREATE TABLE dim_product AS SELECT * FROM (VALUES ('SYN_1','D1','CAT'),('SYN_2','D2','CAT')) t(item_id,dept_id,cat_id);
            CREATE TABLE mart_sales_daily AS SELECT date,store_id,item_id,dept_id,state_id,
                (date_diff('day',date '2020-01-01',date)//4)::INT AS wm_yr_wk,
                CASE WHEN item_id='SYN_1' THEN 1 ELSE 10 END::BIGINT AS units,
                CASE WHEN date=date '2020-01-01' THEN NULL ELSE 2.0 END::DOUBLE AS sell_price,
                units*sell_price AS revenue_proxy,1.0::DOUBLE AS rolling_7d,2.0::DOUBLE AS rolling_28d,
                NULL::DOUBLE AS price_change_pct,date=date '2020-01-04' AS demand_spike_flag
            FROM dim_calendar CROSS JOIN dim_store CROSS JOIN dim_product;
            CREATE VIEW mart_demand_alerts AS SELECT * FROM mart_sales_daily WHERE demand_spike_flag;
            CREATE TABLE pipeline_metadata AS SELECT 'synthetic-gold' AS gold_run_id,
                'synthetic-silver' AS silver_run_id,'synthetic-bronze' AS bronze_run_id,
                date '2020-01-01' AS first_sales_date,date '2020-01-08' AS last_sales_date,
                date '2020-01-10' AS as_of_date;
            CREATE TABLE model_run AS SELECT 'lightgbm_global_v1' AS model,repeat('a',64) AS freeze_sha256;
            CREATE TABLE fact_forecast AS SELECT
                CASE WHEN date<date '2020-01-05' THEN date '2020-01-02' ELSE date '2020-01-06' END AS forecast_origin,
                date AS target_date,store_id,item_id,model,
                CASE WHEN date<date '2020-01-05' THEN 'validation' ELSE 'test' END AS split,
                date_diff('day',forecast_origin,date)::INT AS horizon,
                CASE WHEN item_id='SYN_1' THEN 'low' ELSE 'high' END AS demand_level,
                (units+CASE WHEN item_id='SYN_1' THEN 2 ELSE 1 END*multiplier)::DOUBLE AS predicted_units,
                units::DOUBLE AS actual_units,'synthetic-gold' AS source_run_id
            FROM mart_sales_daily CROSS JOIN (VALUES ('last_value',1),('rolling_mean',2),
                ('seasonal_naive_7',3),('lightgbm_global_v1',4)) m(model,multiplier)
            WHERE date IN (date '2020-01-03',date '2020-01-04',date '2020-01-07',date '2020-01-08');
            CREATE TABLE forecast_evaluation AS SELECT model,split,'overall' AS segment_type,
                count(*) AS observations,sum(abs(actual_units-predicted_units))/sum(abs(actual_units)) AS WMAPE,
                avg(abs(actual_units-predicted_units)) AS MAE,sqrt(avg(pow(actual_units-predicted_units,2))) AS RMSE
            FROM fact_forecast GROUP BY model,split;
            INSERT INTO fact_forecast SELECT date '2020-01-08',date '2020-01-09','SYN_A','SYN_1',
                'rolling_mean','future',1,'low',2,NULL,'synthetic-gold';
        """)
    return output


def connect(output):
    return duckdb.connect(str(output / "gold/retailpulse.duckdb"))


def test_exports_deterministic_and_local_only(bi_gold, tmp_path):
    first = export_bi(bi_gold, tmp_path / "bi", SQL)
    second = export_bi(bi_gold, tmp_path / "bi", SQL)
    assert first == second
    assert first["tables"]["forecast"]["rows"] == 64
    assert first["tables"]["sales_daily"]["rows"] == 32
    assert first["tables"]["sales_product_week"]["rows"] == 8
    assert not (bi_gold / "bronze").exists()
    with connect(bi_gold) as db:
        assert db.execute("SELECT count(*) FROM fact_forecast").fetchone()[0] == 65


def test_filtered_grains_and_revenue_nulls(bi_gold):
    with connect(bi_gold) as db:
        prepare_views(db, SQL)
        # All unknown prices on the first day remain unknown, not a known zero.
        assert db.execute("SELECT sum(known_revenue_proxy),sum(priced_count) FROM bi_sales_daily WHERE date='2020-01-01'").fetchone() == (None, 0)
        assert db.execute("SELECT sum(units),sum(known_revenue_proxy),sum(priced_count),sum(observation_count) FROM bi_sales_daily WHERE store_id='SYN_A' AND dept_id='D2'").fetchone() == (80, 140, 7, 8)
        assert db.execute("SELECT sum(units) FROM bi_sales_product_week WHERE store_id='SYN_A' AND item_id='SYN_2' AND week_key=0").fetchone()[0] == 40
        assert db.execute("SELECT sum(units) FROM bi_sales_daily").fetchone()[0] == 176
        assert db.execute("SELECT sum(units) FROM bi_sales_product_week").fetchone()[0] == 176


def test_weighted_forecasts_filters_and_coexistence(bi_gold):
    with connect(bi_gold) as db:
        prepare_views(db, SQL)
        wmape, mae, rmse, n = db.execute("SELECT sum(absolute_error)/sum(actual_units),avg(absolute_error),sqrt(avg(squared_error)),count(*) FROM bi_forecast WHERE model='rolling_mean' AND split='test' AND store_id='SYN_A' AND horizon=1").fetchone()
        assert (wmape, mae, rmse, n) == pytest.approx((6/11, 3, 10**0.5, 2))
        assert wmape != pytest.approx((4/1+2/10)/2)  # Unweighted segment ratios are wrong.
        assert db.execute("SELECT count(DISTINCT model),count(DISTINCT split) FROM bi_forecast").fetchone() == (4, 2)
        assert db.execute("SELECT sum(actual) FROM (SELECT forecast_origin,target_date,store_id,item_id,split,max(actual_units) actual FROM bi_forecast GROUP BY ALL)").fetchone()[0] == 88
        assert db.execute((SQL / "checks/bi_reconciliation.sql").read_text()).fetchall() == []


@pytest.mark.parametrize("mutation,match", [
    ("DROP TABLE dim_store", "Gold table: dim_store"),
    ("ALTER TABLE dim_store DROP state_id", "missing columns"),
    ("DELETE FROM fact_forecast WHERE model='rolling_mean'", "all three baselines"),
    ("INSERT INTO dim_product SELECT * FROM dim_product LIMIT 1", "Duplicate BI key"),
    ("UPDATE forecast_evaluation SET MAE=NULL", "forecast_metrics"),
    ("UPDATE fact_forecast SET source_run_id=NULL", "lineage"),
    ("UPDATE fact_forecast SET horizon=99", "forecast_horizon"),
])
def test_invalid_contracts_rejected(bi_gold, mutation, match):
    with connect(bi_gold) as db:
        db.execute(mutation)
        with pytest.raises(ValueError, match=match):
            prepare_views(db, SQL)


def test_missing_local_data(tmp_path):
    with pytest.raises(ValueError, match="Gold database missing"):
        export_bi(tmp_path, tmp_path / "bi", SQL)
    with duckdb.connect() as db, pytest.raises(ValueError, match="requires Gold table"):
        validate_source(db)


def test_report_bindings_and_layout():
    spec = importlib.util.spec_from_file_location("validate_project", ROOT / "dashboards/powerbi/validate_project.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.validate()
    assert result["pages"] == 3 and result["measures"] == 34 and result["tables"] == 15
