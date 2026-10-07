"""Transactional coexistence of baseline and frozen ML forecasts in Gold."""
import json

import pandas as pd

from retailpulse.models.candidate import MODEL_NAME
from retailpulse.models.metrics import segmented_metrics
from retailpulse.quality.checks import require, unique


def persist_model(db, forecasts, evidence):
    unique(forecasts, ["forecast_origin", "target_date", "store_id", "item_id", "model", "split"],
           "ML forecast grain")
    require(set(forecasts["model"]) == {MODEL_NAME}, "Unexpected ML model name")
    require(set(forecasts["split"]) == {"validation", "test"}, "Both evaluated splits required")
    require(set(forecasts["source_run_id"]) == {evidence["source_run_id"]}, "Mixed Gold sources")
    source = db.execute("SELECT gold_run_id FROM pipeline_metadata").fetchone()[0]
    require(source == evidence["source_run_id"], "Gold source changed since model freeze")
    for split, window in evidence["winner"]["windows"].items():
        block = forecasts.loc[forecasts["split"].eq(split)]
        series = db.execute("SELECT store_id, item_id FROM mart_sales_daily WHERE date = ?",
                            [pd.Timestamp(window["origin"])]).fetchdf()
        require(len(block) == len(series) * window["days"]
                and set(block["horizon"]) == set(range(1, window["days"] + 1))
                and block["forecast_origin"].eq(pd.Timestamp(window["origin"])).all()
                and set(zip(block["store_id"], block["item_id"], strict=True))
                == set(zip(series["store_id"], series["item_id"], strict=True)),
                "Forecast reconciliation failed: incomplete origin/series/horizon coverage")
    require(bool((forecasts["training_end"] == forecasts["forecast_origin"]).all()
                 and (forecasts["training_start"] <= forecasts["training_end"]).all()
                 and ((forecasts["target_date"] - forecasts["forecast_origin"]).dt.days
                      == forecasts["horizon"]).all()), "Invalid forecast temporal bounds")
    metrics = segmented_metrics(forecasts)
    metadata = pd.DataFrame([{"model": MODEL_NAME, "source_run_id": source,
                              "freeze_sha256": evidence["freeze_sha256"],
                              "mlflow_run_id": evidence["final_run_id"],
                              "evidence_json": json.dumps(evidence, sort_keys=True)}])
    for name, frame in [("ml_forecasts", forecasts), ("ml_metrics", metrics), ("ml_run", metadata)]:
        db.register(name, frame)
    db.execute("BEGIN TRANSACTION")
    try:
        db.execute("DELETE FROM fact_forecast WHERE model = ?", [MODEL_NAME])
        db.execute("DELETE FROM forecast_evaluation WHERE model = ?", [MODEL_NAME])
        db.execute("INSERT INTO fact_forecast BY NAME SELECT * FROM ml_forecasts")
        db.execute("INSERT INTO forecast_evaluation BY NAME SELECT * FROM ml_metrics")
        db.execute("CREATE TABLE IF NOT EXISTS model_run AS SELECT * FROM ml_run LIMIT 0")
        db.execute("DELETE FROM model_run WHERE model = ?", [MODEL_NAME])
        db.execute("INSERT INTO model_run BY NAME SELECT * FROM ml_run")
        db.execute("COMMIT")
    except Exception:
        db.execute("ROLLBACK")
        raise
    finally:
        for name in ("ml_forecasts", "ml_metrics", "ml_run"):
            db.unregister(name)
    return metrics
