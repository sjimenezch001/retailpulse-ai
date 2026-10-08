"""Author distribution-safe snapshots with canonical Gold SQL; never read real M5.

Normal demo startup loads these CSVs; it does not execute this authoring script.
"""

import json
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

import duckdb

from retailpulse.ingestion.bronze import ingest
from retailpulse.models.baseline import run_baselines
from retailpulse.transforms.gold import run_gold
from retailpulse.transforms.silver import run_silver

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "src/retailpulse/api/synthetic"


def main():
    DESTINATION.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory() as temporary:
        output = Path(temporary)
        ingest(ROOT / "tests/fixtures/m5_synthetic", output / "bronze")
        run_silver(output, ["SYN_A", "SYN_B", "SYN_C"], ["SYN_D1", "SYN_D2"])
        run_gold(output, ROOT / "sql", date(2020, 2, 12))
        run_baselines(output, validation_days=7, test_days=7, future_horizon=7)
        with duckdb.connect(str(output / "gold/retailpulse.duckdb")) as db:
            # Deliberately simulated comparison series. No LightGBM training or real forecasts.
            db.execute("""INSERT INTO fact_forecast SELECT forecast_origin,target_date,store_id,item_id,dept_id,
                'lightgbm_global_v1',split,horizon,
                CASE WHEN horizon=7 AND store_id='SYN_A' THEN actual_units+18 ELSE actual_units*0.9 END,
                actual_units,demand_level,training_start,training_end,'synthetic-web-v1'
                FROM fact_forecast WHERE model='rolling_mean' AND split!='future'""")
            db.execute("UPDATE fact_forecast SET source_run_id='synthetic-web-v1'")
            db.execute("""UPDATE pipeline_metadata SET gold_run_id='synthetic-web-v1',
                silver_run_id='synthetic-silver-v1',bronze_run_id='synthetic-bronze-v1',
                source_ingestion_ts='2020-02-12T00:00:00+00:00',generated_at='2020-02-12T00:00:00+00:00',identity_json='{}'""")
            # This is metadata/CSV export only; runtime metrics reuse GoldTools.
            names = (
                "mart_sales_daily",
                "dim_store",
                "dim_product",
                "pipeline_metadata",
                "fact_forecast",
                "metric_definitions",
            )
            schemas = {}
            for name in names:
                columns = db.execute(f'DESCRIBE "{name}"').fetchall()
                schemas[name] = ",".join(f'"{row[0]}" {row[1]}' for row in columns)
                frame = db.execute(f'SELECT * FROM "{name}"').fetchdf()
                if name == "mart_sales_daily":
                    # Remove author-machine lineage; only deterministic synthetic identifiers survive.
                    for column in ("pipeline_run_id", "source_file", "ingestion_ts"):
                        if column in frame:
                            frame[column] = (
                                "2020-02-12T00:00:00+00:00"
                                if column == "ingestion_ts"
                                else "synthetic-fixture"
                            )
                frame = frame.sort_values(list(frame.columns), kind="stable")
                frame.to_csv(
                    DESTINATION / f"{name}.csv", index=False, lineterminator="\n"
                )
            (DESTINATION / "manifest.json").write_text(
                json.dumps(
                    {
                        "mode": "synthetic",
                        "version": "synthetic-web-v1",
                        "source": "Repository-authored m5_synthetic fixtures only; simulated LightGBM comparison, no training.",
                        "tables": schemas,
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )


if __name__ == "__main__":
    main()
