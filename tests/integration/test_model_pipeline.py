import duckdb
import numpy as np
import pandas as pd
import pytest

from retailpulse.features.forecast import load_panel
from retailpulse.models import workflow
from retailpulse.models.baseline import run_baselines
from retailpulse.models.candidate import MODEL_NAME
from retailpulse.models.persistence import persist_model
from retailpulse.models.tracking import read_json
from retailpulse.quality.checks import QualityError


def test_gold_loader_ignores_future_sales_and_prices(model_gold):
    with duckdb.connect(str(model_gold / "gold/retailpulse.duckdb")) as db:
        first = load_panel(db, "2020-03-24", 40)
        db.execute("UPDATE mart_sales_daily SET units=999999, sell_price=999 "
                   "WHERE date > DATE '2020-03-24'")
        second = load_panel(db, "2020-03-24", 40)
        np.testing.assert_array_equal(first.units, second.units)
        np.testing.assert_array_equal(first.prices, second.prices)
        assert len(first.dates) == 40 + 28
        assert first.dates[-1] == pd.Timestamp("2020-03-24")
        db.execute("DELETE FROM mart_sales_daily WHERE date=DATE '2020-03-01' AND store_id='SYN_A'")
        with pytest.raises(QualityError, match="Incomplete"):
            load_panel(db, "2020-03-24", 40)


def test_model_freeze_isolation_persistence_and_rerun(model_gold, tiny_candidates, tmp_path, monkeypatch):
    baseline = run_baselines(model_gold)
    path = model_gold / "gold/retailpulse.duckdb"
    with duckdb.connect(str(path)) as db:
        before = db.execute("SELECT * FROM fact_forecast ORDER BY ALL").fetchdf()
    artifacts = tmp_path / "artifacts"
    calls = []
    original = workflow.attach_actuals

    def guarded_actuals(db, forecasts):
        split = forecasts["split"].iloc[0]
        if split == "test":
            assert (artifacts / "rp07/synthetic-model-gold/freeze.json").is_file()
        calls.append(split)
        return original(db, forecasts)

    monkeypatch.setattr(workflow, "attach_actuals", guarded_actuals)
    args = dict(training_days=50, candidates=tiny_candidates)
    frozen = workflow.run_model(model_gold, artifacts, validation_only=True, **args)
    assert frozen["test_evaluated"] is False
    assert calls == ["validation", "validation"]
    result = workflow.run_model(model_gold, artifacts, **args)
    assert calls == ["validation", "validation", "test"]
    second = workflow.run_model(model_gold, artifacts, **args)
    assert second["reused"] and result["artifact_hashes"] == second["artifact_hashes"]
    assert calls.count("test") == 1
    assert result["forecast_rows"] == 4 * 28 * 2
    run_baselines(model_gold)
    with duckdb.connect(str(path)) as db:
        old = db.execute("SELECT * FROM fact_forecast WHERE model != ? ORDER BY ALL", [MODEL_NAME]).fetchdf()
        pd.testing.assert_frame_equal(before, old)
        assert len(old) == baseline["forecast_rows"]
        forecasts = db.execute("SELECT * FROM fact_forecast WHERE model=? ORDER BY ALL", [MODEL_NAME]).fetchdf()
        assert len(forecasts) == result["forecast_rows"]
        assert not forecasts.duplicated(["forecast_origin", "target_date", "store_id", "item_id", "model", "split"]).any()
        assert (forecasts["training_end"] < forecasts["target_date"]).all()
        assert (forecasts["training_end"] == forecasts["forecast_origin"]).all()
        with pytest.raises(QualityError, match="duplicate key"):
            persist_model(db, pd.concat([forecasts, forecasts.iloc[:1]]), result)
        with pytest.raises(QualityError, match="reconciliation"):
            persist_model(db, forecasts.iloc[1:], result)
        assert db.execute("SELECT count(*) FROM model_run").fetchone() == (1,)
        assert db.execute("SELECT count(*) FROM fact_forecast WHERE model=?", [MODEL_NAME]).fetchone() == (224,)
    audit = read_json(artifacts / "rp07/synthetic-model-gold/audit.json")
    names = [entry["event"] for entry in audit]
    assert names.index("winner_frozen") < names.index("final_model_trained") < names.index("test_evaluation_started")
    assert names.count("test_evaluation_started") == names.count("test_evaluation_completed") == 1
    assert (artifacts / "mlflow/mlflow.db").is_file()
    with pytest.raises(QualityError, match="immutable"):
        workflow.run_model(model_gold, artifacts, training_days=49, candidates=tiny_candidates)


def test_interrupted_test_does_not_silently_reevaluate(model_gold, tiny_candidates, tmp_path, monkeypatch):
    run_baselines(model_gold)
    artifacts = tmp_path / "artifacts"
    kwargs = dict(training_days=40, candidates=tiny_candidates[:1])
    workflow.run_model(model_gold, artifacts, validation_only=True, **kwargs)

    def interrupted(*args):
        raise RuntimeError("simulated evaluation interruption")

    monkeypatch.setattr(workflow, "attach_actuals", interrupted)
    with pytest.raises(RuntimeError, match="interruption"):
        workflow.run_model(model_gold, artifacts, **kwargs)
    with pytest.raises(QualityError, match="started without a saved result"):
        workflow.run_model(model_gold, artifacts, **kwargs)
