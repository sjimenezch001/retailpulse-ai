"""DuckDB is the canonical serving layer for analytical metrics."""
import hashlib
import json
from datetime import UTC, date, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

import duckdb
import pandas as pd

from retailpulse.data.snapshots import read_snapshot, snapshot_id
from retailpulse.data.source import utc_now
from retailpulse.quality.checks import require, unique

GOLD_VERSION = "gold-v1"


def build_gold(connection, tables: dict[str, pd.DataFrame], sql_root: Path,
               as_of: date) -> None:
    fact = tables["fact_sales_daily"]
    unique(fact, ["date", "store_id", "item_id"], "Gold input")
    require(not fact.empty, "Empty Gold input")
    require(as_of >= fact["date"].max().date(), "as_of precedes latest observed sales date")
    # Silver ensures complete daily series; check again at the window boundary.
    sizes = fact.groupby(["store_id", "item_id"], observed=True)["date"].agg(["min", "max", "count"])
    require(bool(((sizes["max"] - sizes["min"]).dt.days + 1 == sizes["count"]).all()),
            "Gold requires complete daily series for row-based windows")
    for name, frame in tables.items():
        require(name.isidentifier(), "Invalid Gold table name")
        frame = frame.copy()
        if name == "dim_calendar":
            for field in ("event_name_1", "event_name_2"):
                if field not in frame:
                    frame[field] = pd.Series(None, index=frame.index, dtype="string")
        connection.register("input_table", frame)
        connection.execute(f'CREATE TABLE "{name}" AS SELECT * FROM input_table')
        connection.unregister("input_table")
    connection.execute((sql_root / "gold/mart_sales_daily.sql").read_text(encoding="utf-8"), [as_of])
    connection.execute((sql_root / "gold/mart_store_weekly.sql").read_text(encoding="utf-8"))
    connection.execute((sql_root / "gold/interfaces.sql").read_text(encoding="utf-8"))
    failures = connection.execute((sql_root / "checks/gold_quality.sql").read_text(encoding="utf-8")).fetchall()
    require(not failures, f"Gold quality failures: {failures}")


def run_gold(output: Path, sql_root: Path, as_of: date | None = None) -> dict:
    tables, silver = read_snapshot(output / "silver")
    as_of = as_of or datetime.now(UTC).date()
    sql_digest = hashlib.sha256()
    for path in sorted([*(sql_root / "gold").glob("*.sql"), *(sql_root / "checks").glob("*.sql")]):
        sql_digest.update(path.name.encode() + path.read_bytes())
    identity = {"version": GOLD_VERSION, "silver_run_id": silver["pipeline_run_id"],
                "as_of": as_of.isoformat(), "sql_sha256": sql_digest.hexdigest()}
    run_id = snapshot_id(identity)
    directory = output / "gold"
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / "retailpulse.duckdb"
    # Preserve an unchanged database, including forecasts subsequently added by RP-06.
    if target.exists():
        with duckdb.connect(str(target), read_only=True) as existing:
            stored = existing.execute("SELECT gold_run_id FROM pipeline_metadata").fetchone()
            if stored == (run_id,):
                failures = existing.execute((sql_root / "checks/gold_quality.sql").read_text(encoding="utf-8")).fetchall()
                require(not failures, f"Existing Gold quality failures: {failures}")
                return {"gold_run_id": run_id, "reused": True}
    fact = tables["fact_sales_daily"]
    with TemporaryDirectory(prefix="staging-", dir=directory) as temporary:
        staged = Path(temporary) / "retailpulse.duckdb"
        with duckdb.connect(str(staged)) as connection:
            build_gold(connection, tables, sql_root, as_of)
            metadata = pd.DataFrame([{
                "gold_run_id": run_id, "silver_run_id": silver["pipeline_run_id"],
                "bronze_run_id": silver["identity"]["bronze_run_id"],
                "first_sales_date": fact["date"].min().date(),
                "last_sales_date": fact["date"].max().date(), "as_of_date": as_of,
                "source_ingestion_ts": fact["ingestion_ts"].max(), "generated_at": utc_now(),
                "identity_json": json.dumps(identity, sort_keys=True),
            }])
            connection.register("metadata_input", metadata)
            connection.execute("CREATE TABLE pipeline_metadata AS SELECT * FROM metadata_input")
        staged.replace(target)
    return {"gold_run_id": run_id, "reused": False, "sales_rows": len(fact),
            "units": int(fact["units"].sum())}
