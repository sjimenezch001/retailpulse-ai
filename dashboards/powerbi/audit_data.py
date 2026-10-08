"""Read-only real-data audit. Publish aggregate evidence, never observations."""
import hashlib
import json
import math
from pathlib import Path

import duckdb

from retailpulse.bi.export import prepare_views

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def audit():
    gold = ROOT / "data/processed/gold/retailpulse.duckdb"
    before = sha(gold)
    data = ROOT / "artifacts/powerbi/data"
    manifest = json.loads((data / "manifest.json").read_text())
    for spec in manifest["tables"].values():
        assert sha(data / spec["file"]) == spec["sha256"]
    evidence = {"source_run_id": manifest["source_run_id"], "manifest_sha256": sha(data / "manifest.json"),
                "exports": {name: {key: spec[key] for key in ("rows", "sha256", "bytes")} for name, spec in manifest["tables"].items()}}
    with duckdb.connect(str(gold), read_only=True) as db:
        db.execute("SET threads=1")
        prepare_views(db, ROOT / "sql")
        evidence["lineage"] = db.execute("SELECT * FROM bi_metadata").fetchdf().to_dict(orient="records")[0]
        evidence["gold_tables"] = {name: db.execute(f"SELECT count(*) FROM {name}").fetchone()[0] for name in ("mart_sales_daily", "mart_store_weekly", "mart_demand_alerts", "fact_forecast", "forecast_evaluation", "model_run", "dim_calendar", "dim_product", "dim_store")}
        evidence["sales"] = db.execute("""SELECT sum(units) units,sum(revenue_proxy) known_revenue_proxy,
            count(*) observations,count(sell_price) priced_observations,count(*)-count(sell_price) missing_prices,
            CASE WHEN count(sell_price)=count(*) THEN sum(revenue_proxy) END canonical_revenue_proxy,
            count(sell_price)::DOUBLE/count(*) price_coverage FROM mart_sales_daily""").fetchdf().to_dict(orient="records")[0]
        evidence["forecast_metrics"] = db.execute("SELECT model,split,count(*) observations,sum(absolute_error)/sum(actual_units) WMAPE,avg(absolute_error) MAE,sqrt(avg(squared_error)) RMSE FROM bi_forecast GROUP BY model,split ORDER BY model,split").fetchdf().to_dict(orient="records")
        # Verify exported values, not only the temporary SQL views that produce them.
        for name in ("sales_daily", "sales_product_week", "forecast"):
            path = (data / f"{name}.csv").as_posix().replace("'", "''")
            db.execute(f"CREATE TEMP VIEW exported_{name} AS SELECT * FROM read_csv_auto('{path}')")
        checks = []
        def compare(name, left, right):
            actual, expected = db.execute(left).fetchall(), db.execute(right).fetchall()
            assert len(actual) == len(expected), name
            for row, reference in zip(actual, expected, strict=True):
                for a, b in zip(row, reference, strict=True):
                    if isinstance(a, float):
                        assert math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-8), (name, a, b)
                    else:
                        assert a == b, (name, a, b)
            checks.append({"check": name, "groups": len(actual), "status": "PASS"})
        compare("daily_date_store_department", "SELECT store_id,dept_id,sum(units),sum(known_revenue_proxy),sum(priced_count),sum(observation_count) FROM exported_sales_daily WHERE date BETWEEN '2016-03-28' AND '2016-05-22' GROUP BY ALL ORDER BY 1,2",
                "SELECT store_id,dept_id,sum(units),sum(revenue_proxy),count(sell_price),count(*) FROM mart_sales_daily WHERE date BETWEEN '2016-03-28' AND '2016-05-22' GROUP BY ALL ORDER BY 1,2")
        compare("product_week_store_product", "SELECT store_id,item_id,sum(units),sum(priced_count),sum(observation_count) FROM exported_sales_product_week JOIN bi_week USING(week_key) WHERE week_start BETWEEN '2016-03-26' AND '2016-05-21' GROUP BY ALL ORDER BY 1,2",
                "SELECT store_id,item_id,sum(units),count(sell_price),count(*) FROM mart_sales_daily WHERE wm_yr_wk IN (SELECT week_key FROM bi_week WHERE week_start BETWEEN '2016-03-26' AND '2016-05-21') GROUP BY ALL ORDER BY 1,2")
        compare("forecast_model_split_store_department_demand_horizon", "SELECT model,split,store_id,p.dept_id,demand_level,horizon,sum(absolute_error)/nullif(sum(abs(actual_units)),0),avg(absolute_error),sqrt(avg(squared_error)),count(*) FROM exported_forecast JOIN dim_product p USING(item_id) GROUP BY ALL ORDER BY 1,2,3,4,5,6",
                "SELECT model,split,store_id,p.dept_id,demand_level,horizon,sum(abs(actual_units-predicted_units))/nullif(sum(abs(actual_units)),0),avg(abs(actual_units-predicted_units)),sqrt(avg(pow(actual_units-predicted_units,2))),count(*) FROM fact_forecast JOIN dim_product p USING(item_id) WHERE actual_units IS NOT NULL GROUP BY ALL ORDER BY 1,2,3,4,5,6")
        evidence["independent_filter_checks"] = checks
    evidence["gold_sha256"] = before
    assert sha(gold) == before, "Gold changed during audit"
    evidence["gold_unchanged_during_audit"] = True
    frozen = ROOT / "artifacts/rp07" / manifest["source_run_id"]
    evidence["frozen_artifact_hashes"] = {str(path.relative_to(frozen)).replace("\\", "/"): sha(path) for path in sorted(frozen.rglob("*")) if path.is_file()}
    evidence["sql_reconciliation"] = "PASS"
    # JSON null, not nonstandard NaN, for the incomplete canonical revenue.
    evidence["sales"]["canonical_revenue_proxy"] = None if math.isnan(evidence["sales"]["canonical_revenue_proxy"]) else evidence["sales"]["canonical_revenue_proxy"]
    target = ROOT / "docs/evidence/rp08_data_audit.json"
    target.write_text(json.dumps(evidence, indent=2, default=str, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "filter_checks": checks, "evidence": str(target.relative_to(ROOT))}, indent=2))


if __name__ == "__main__":
    audit()
