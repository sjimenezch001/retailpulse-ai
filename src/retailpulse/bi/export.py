"""Deterministic CSV exports; no Bronze dependency and no Gold mutations."""
import hashlib
import json
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

import duckdb

from retailpulse.quality.checks import require

TABLES = {
    "date": ["date"], "week": ["week_key"], "store": ["store_id"],
    "department": ["dept_id"], "product": ["item_id"], "model": ["model"],
    "split": ["split"], "demand_level": ["demand_level"], "horizon": ["horizon"],
    "sales_daily": ["date", "store_id", "dept_id"],
    "sales_product_week": ["week_key", "store_id", "item_id"],
    "forecast": ["forecast_origin", "target_date", "store_id", "item_id", "model", "split"],
    "metadata": ["gold_run_id"],
}
REQUIRED = {
    "mart_sales_daily": ["date", "store_id", "item_id", "dept_id", "state_id", "wm_yr_wk", "units",
                         "sell_price", "revenue_proxy", "rolling_7d", "rolling_28d", "price_change_pct", "demand_spike_flag"],
    "dim_calendar": ["date", "year", "month", "weekday", "event_name_1", "event_name_2", "snap_CA", "snap_TX", "snap_WI"],
    "dim_store": ["store_id", "state_id"], "dim_product": ["item_id", "dept_id", "cat_id"],
    "fact_forecast": ["forecast_origin", "target_date", "store_id", "item_id", "model", "split", "horizon",
                      "demand_level", "predicted_units", "actual_units", "source_run_id"],
    "forecast_evaluation": ["model", "split", "segment_type", "observations", "WMAPE", "MAE", "RMSE"],
    "mart_demand_alerts": ["date"], "model_run": ["model", "freeze_sha256"],
    "pipeline_metadata": ["gold_run_id", "silver_run_id", "bronze_run_id", "first_sales_date", "last_sales_date", "as_of_date"],
}


def validate_source(db):
    names = {row[0] for row in db.execute("SHOW TABLES").fetchall()}
    for table, required in REQUIRED.items():
        require(table in names, f"BI requires Gold table: {table}")
        columns = {row[0] for row in db.execute(f'DESCRIBE "{table}"').fetchall()}
        require(set(required) <= columns, f"BI missing columns in {table}: {sorted(set(required)-columns)}")
    require(db.execute("SELECT count(*) FROM pipeline_metadata").fetchone()[0] == 1,
            "BI requires one Gold metadata record")
    require(db.execute("SELECT count(*) FROM model_run WHERE model='lightgbm_global_v1'").fetchone()[0] == 1,
            "BI requires the completed RP-07 frozen model")
    models = {row[0] for row in db.execute("SELECT DISTINCT model FROM fact_forecast WHERE actual_units IS NOT NULL").fetchall()}
    require(models == {"last_value", "rolling_mean", "seasonal_naive_7", "lightgbm_global_v1"},
            "BI requires all three baselines and the frozen RP-07 model")


def prepare_views(db, sql_root):
    validate_source(db)
    db.execute((Path(sql_root) / "bi/serving.sql").read_text(encoding="utf-8"))
    for name, keys in TABLES.items():
        key_sql = ", ".join(keys)
        require(not db.execute(f"SELECT 1 FROM bi_{name} GROUP BY {key_sql} HAVING count(*)>1 LIMIT 1").fetchall(),
                f"Duplicate BI key: {name}")
        nulls = " OR ".join(f"{key} IS NULL" for key in keys)
        require(not db.execute(f"SELECT 1 FROM bi_{name} WHERE {nulls} LIMIT 1").fetchall(), f"Null BI key: {name}")
    failures = db.execute((Path(sql_root) / "checks/bi_reconciliation.sql").read_text(encoding="utf-8")).fetchall()
    require(not failures, f"BI reconciliation failed: {failures}")


def export_bi(output: Path, target: Path, sql_root: Path):
    database = Path(output) / "gold/retailpulse.duckdb"
    require(database.is_file(), "Gold database missing; complete RP-02 through RP-07 before export-bi")
    target = Path(target).resolve()
    target.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(database), read_only=True) as db:
        db.execute("SET threads=1")
        db.execute("SET memory_limit='768MB'")
        prepare_views(db, sql_root)
        source = db.execute("SELECT gold_run_id FROM pipeline_metadata").fetchone()[0]
        manifest = {"version": "powerbi-v1", "source_run_id": source, "reconciliation": "PASS", "tables": {}}
        with TemporaryDirectory(prefix="staging-", dir=target) as staging:
            stage = Path(staging).resolve()
            require(stage.is_relative_to(target), "Staging directory escaped BI output")
            for name, keys in TABLES.items():
                path = stage / f"{name}.csv"
                query = f"SELECT * FROM bi_{name} ORDER BY " + ", ".join(keys)
                escaped = str(path).replace("'", "''")
                db.execute(f"COPY ({query}) TO '{escaped}' (FORMAT CSV, HEADER, NULL '')")
                columns = [{"name": row[0], "type": row[1]} for row in db.execute(f"DESCRIBE bi_{name}").fetchall()]
                with path.open("rb") as stream:
                    checksum = hashlib.file_digest(stream, "sha256").hexdigest()
                manifest["tables"][name] = {"file": path.name, "rows": db.execute(f"SELECT count(*) FROM bi_{name}").fetchone()[0],
                                             "columns": columns, "keys": keys, "sha256": checksum,
                                             "bytes": path.stat().st_size}
            # The manifest is published last; refresh only after the command succeeds.
            # A Windows TemporaryDirectory has a private DACL. Copy into the output
            # directory before atomic replacement so Desktop inherits its read access.
            for path in stage.glob("*.csv"):
                publish(path, target / path.name)
            manifest_path = stage / "manifest.json"
            manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            publish(manifest_path, target / "manifest.json")
    return manifest


def publish(source, destination):
    temporary = destination.parent / (".publishing-" + uuid4().hex)
    try:
        shutil.copyfile(source, temporary)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
