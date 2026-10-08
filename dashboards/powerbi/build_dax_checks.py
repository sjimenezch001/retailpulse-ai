"""Create SQL expectations for live Desktop DAX verification (aggregate values only)."""
import json
from pathlib import Path

import duckdb

from retailpulse.bi.export import prepare_views

ROOT = Path(__file__).resolve().parents[2]


def build():
    cases = []
    with duckdb.connect(str(ROOT / "data/processed/gold/retailpulse.duckdb"), read_only=True) as db:
        db.execute("SET threads=1")
        prepare_views(db, ROOT / "sql")

        def case(name, dax, sql):
            cursor = db.execute(sql)
            expected = dict(zip([col[0] for col in cursor.description], cursor.fetchone(), strict=True))
            cases.append({"name": name, "dax": dax, "expected": expected})

        case("full_sales", 'EVALUATE ROW("units",[Total Units],"revenue",[Known Revenue Proxy],"coverage",[Price Coverage],"canonical",[Canonical Revenue Proxy],"freshness",[Data Freshness])',
             "SELECT sum(units) units,sum(revenue_proxy) revenue,count(sell_price)::DOUBLE/count(*) coverage,CASE WHEN count(sell_price)=count(*) THEN sum(revenue_proxy) END canonical,3790 freshness FROM mart_sales_daily")
        case("daily_date_store_department", '''EVALUATE CALCULATETABLE(ROW("units",[Total Units],"revenue",[Known Revenue Proxy],"coverage",[Price Coverage],"previous",[Previous Period Units],"change",[Period-over-Period Change %]), DATESBETWEEN('Date'[Date],DATE(2016,3,28),DATE(2016,5,22)),'Store'[Store]="CA_1",Department[Department]="FOODS_1")''',
             "WITH p AS (SELECT sum(units) FILTER(WHERE date BETWEEN '2016-02-01' AND '2016-03-27') previous FROM mart_sales_daily WHERE store_id='CA_1' AND dept_id='FOODS_1') SELECT sum(units) units,sum(revenue_proxy) revenue,count(sell_price)::DOUBLE/count(*) coverage,(SELECT previous FROM p) previous,(sum(units)-(SELECT previous FROM p))::DOUBLE/(SELECT previous FROM p) change FROM mart_sales_daily WHERE store_id='CA_1' AND dept_id='FOODS_1' AND date BETWEEN '2016-03-28' AND '2016-05-22'")
        case("weekly_date_store_department_product", '''EVALUATE CALCULATETABLE(ROW("units",[Product Units],"coverage",[Product Price Coverage],"events",[Event-period Units],"snap",[SNAP-period Units],"spikes",[Product Spike Count]),DATESBETWEEN('Week'[Week Start],DATE(2016,3,26),DATE(2016,5,21)),'Store'[Store]="CA_2",Department[Department]="FOODS_1",Product[Product]="FOODS_1_001")''',
             "SELECT sum(units) units,sum(priced_count)::DOUBLE/sum(observation_count) coverage,sum(event_units) events,sum(snap_units) snap,sum(spike_count) spikes FROM bi_sales_product_week JOIN bi_week USING(week_key) WHERE store_id='CA_2' AND item_id='FOODS_1_001' AND week_start BETWEEN '2016-03-26' AND '2016-05-21'")
        for split in ("validation", "test"):
            for model in ("last_value", "rolling_mean", "seasonal_naive_7", "lightgbm_global_v1"):
                case(f"forecast_{model}_{split}", f'''EVALUATE CALCULATETABLE(ROW("actual",[Actual Units],"predicted",[Predicted Units],"WMAPE",[WMAPE],"MAE",[MAE],"RMSE",[RMSE],"bias",[Forecast Bias]),'Model'[ModelKey]="{model}",Split[Split]="{split}")''',
                     f"SELECT sum(actual_units) actual,sum(predicted_units) predicted,sum(absolute_error)/sum(actual_units) WMAPE,avg(absolute_error) MAE,sqrt(avg(squared_error)) RMSE,sum(signed_error)/sum(actual_units) bias FROM bi_forecast WHERE model='{model}' AND split='{split}'")
        case("forecast_all_slicers", '''EVALUATE CALCULATETABLE(ROW("actual",[Actual Units],"WMAPE",[WMAPE],"MAE",[MAE],"RMSE",[RMSE]),'Model'[ModelKey]="lightgbm_global_v1",Split[Split]="test",'Store'[Store]="CA_3",Department[Department]="FOODS_2",Horizon[Horizon]=7,Demand[Demand Level]="low",DATESBETWEEN('Date'[Date],DATE(2016,4,25),DATE(2016,5,8)))''',
             "SELECT sum(actual_units) actual,sum(absolute_error)/sum(actual_units) WMAPE,avg(absolute_error) MAE,sqrt(avg(squared_error)) RMSE FROM bi_forecast JOIN dim_product USING(item_id) WHERE model='lightgbm_global_v1' AND split='test' AND store_id='CA_3' AND dept_id='FOODS_2' AND horizon=7 AND demand_level='low' AND target_date BETWEEN '2016-04-25' AND '2016-05-08'")
        case("actuals_deduplicated_across_models", 'EVALUATE ROW("actual",[Actual Units],"predicted",[Predicted Units])',
             "SELECT sum(actual) actual,NULL::DOUBLE predicted FROM (SELECT forecast_origin,target_date,store_id,item_id,split,max(actual_units) actual FROM bi_forecast GROUP BY ALL)")
        case("comparison_ignores_only_model_selector", '''EVALUATE CALCULATETABLE(ROW("WMAPE",[Comparison WMAPE],"MAE",[Comparison MAE],"RMSE",[Comparison RMSE]),'Model'[ModelKey]="lightgbm_global_v1",ComparisonModel[ModelKey]="rolling_mean",Split[Split]="test",'Store'[Store]="CA_1")''',
             "SELECT sum(absolute_error)/sum(actual_units) WMAPE,avg(absolute_error) MAE,sqrt(avg(squared_error)) RMSE FROM bi_forecast WHERE model='rolling_mean' AND split='test' AND store_id='CA_1'")
        case("empty_selection_is_blank", '''EVALUATE CALCULATETABLE(ROW("units",[Total Units],"RMSE",[RMSE],"WMAPE",[WMAPE]),FILTER('Date','Date'[Date]>DATE(2020,1,1)))''',
             "SELECT NULL::DOUBLE units,NULL::DOUBLE RMSE,NULL::DOUBLE WMAPE")
        case("cross_fact_filter_isolation", '''EVALUATE CALCULATETABLE(ROW("units",[Total Units]),'Model'[ModelKey]="lightgbm_global_v1",Split[Split]="test")''',
             "SELECT sum(units) units FROM mart_sales_daily")
    target = ROOT / "artifacts/powerbi/dax-checks.json"
    target.write_text(json.dumps(cases, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Prepared {len(cases)} SQL-backed DAX checks.")


if __name__ == "__main__":
    build()
