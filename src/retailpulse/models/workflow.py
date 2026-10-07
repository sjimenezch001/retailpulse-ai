"""Validation-only selection, durable freeze, and one-time held-out evaluation."""
import gc
from contextlib import contextmanager
from importlib.metadata import version
from pathlib import Path

import duckdb
import pandas as pd

from retailpulse.data.source import utc_now
from retailpulse.features.forecast import FEATURE_VERSION, calendar_input, load_panel
from retailpulse.models.candidate import (
    CANDIDATES,
    MODEL_NAME,
    attach_actuals,
    fit_candidate,
    predict_candidate,
    select_candidate,
    temporal_windows,
)
from retailpulse.models.metrics import forecast_metrics, segmented_metrics
from retailpulse.models.persistence import persist_model
from retailpulse.models.tracking import (
    Resources,
    Tracking,
    digest,
    environment,
    file_hash,
    read_json,
    write_json,
)
from retailpulse.quality.checks import require


@contextmanager
def exclusive_run(directory):
    lock = directory / "run.lock"
    try:
        with lock.open("x", encoding="utf-8") as file:
            file.write(utc_now())
    except FileExistsError as exc:
        raise ValueError("RP-07 run is already active; inspect the local run.lock") from exc
    try:
        yield
    finally:
        lock.unlink()


def implementation_hash():
    root = Path(__file__).resolve().parents[1]
    files = sorted([*(root / "features").glob("*.py"), *(root / "models").glob("*.py")])
    return digest({str(path.relative_to(root)): file_hash(path) for path in files})


def event(directory, name, **details):
    path = directory / "audit.json"
    events = read_json(path) if path.exists() else []
    events.append({"event": name, "at": utc_now(), **details})
    write_json(path, events)


def baseline_metrics(db, split):
    frame = db.execute("SELECT * FROM forecast_evaluation WHERE model = 'rolling_mean' "
                       "AND split = ? AND segment_type = 'overall'", [split]).fetchdf()
    require(len(frame) == 1, "Run RP-06 baselines before RP-07")
    return {name: float(frame.iloc[0][name]) for name in ("WMAPE", "MAE", "RMSE")}


def save_model(model, categories, directory):
    directory.mkdir(parents=True, exist_ok=True)
    model.save_model(str(directory / "model.txt"))
    write_json(directory / "categories.json", categories)
    pd.DataFrame({"feature": model.feature_name(),
                  "gain": model.feature_importance(importance_type="gain"),
                  "splits": model.feature_importance(importance_type="split")}).sort_values(
                      ["gain", "feature"], ascending=[False, True]).to_csv(directory / "importance.csv", index=False)


def train_predict(db, window, configuration, metadata, directory, split):
    with Resources() as resources:
        panel = load_panel(db, window["origin"], metadata["training_days"])
        model, categories, details = fit_candidate(panel, configuration)
        calendar = calendar_input(db, window["start"], window["end"])
        predictions = predict_candidate(db, model, panel, calendar, window, configuration,
                                        categories, split, metadata["source_run_id"])
        save_model(model, categories, directory)
        del model, panel
        gc.collect()
    details.update(resources.report())
    write_json(directory / "training.json", details)
    predictions.to_parquet(directory / "predictions.parquet", index=False)
    return predictions, details


def validation_search(db, metadata, directory, tracker):
    results = []
    for configuration in metadata["candidates"]:
        name = configuration["name"]
        require(name.isidentifier(), "Invalid candidate name")
        target = directory / name
        if (target / "result.json").exists():
            results.append(read_json(target / "result.json"))
            continue
        print(f"Training validation candidate {name}", flush=True)
        forecasts, details = train_predict(db, metadata["windows"]["validation"], configuration,
                                          metadata, target, "validation")
        forecasts = attach_actuals(db, forecasts)
        metrics = forecast_metrics(forecasts["actual_units"], forecasts["predicted_units"])
        forecasts.to_parquet(target / "evaluated.parquet", index=False)
        run_id = tracker.log_run(name, configuration, details, metrics, target, metadata, "validation")
        result = {"configuration": configuration, "split": "validation", "metrics": metrics,
                  "details": details, "mlflow_run_id": run_id}
        write_json(target / "result.json", result)
        event(directory, "validation_candidate_completed", candidate=name, mlflow_run_id=run_id)
        print(f"{name}: validation WMAPE={metrics['WMAPE']:.8f}, "
              f"MAE={metrics['MAE']:.6f}, RMSE={metrics['RMSE']:.6f}", flush=True)
        results.append(result)
    winner = select_candidate(results)
    freeze = {"model": MODEL_NAME, "configuration": winner["configuration"],
              "features": winner["details"]["features"], "training_days": metadata["training_days"],
              "feature_version": FEATURE_VERSION, "implementation_sha256": metadata["implementation_sha256"],
              "windows": metadata["windows"], "source_run_id": metadata["source_run_id"],
              "selection_split": "validation", "selection_metric": "WMAPE",
              "validation_metrics": winner["metrics"], "validation_run_id": winner["mlflow_run_id"],
              "plan_sha256": metadata["plan_sha256"]}
    freeze_path = directory / "freeze.json"
    if freeze_path.exists():
        require(read_json(freeze_path)["design"] == freeze, "Frozen design cannot change")
    else:
        write_json(freeze_path, {"frozen_at": utc_now(), "sha256": digest(freeze), "design": freeze})
        event(directory, "winner_frozen", sha256=digest(freeze), winner=winner["configuration"]["name"])
    return results, freeze


def final_evaluation(db, metadata, directory, freeze, tracker):
    final = directory / "final"
    final.mkdir(exist_ok=True)
    outcome = final / "result.json"
    if outcome.exists():
        return read_json(outcome)
    marker = final / "test_evaluation_started.json"
    # Fail closed after an interrupted evaluation; never silently re-open the test.
    require(not marker.exists(), "Test evaluation started without a saved result; inspect local artifacts")
    configuration = freeze["configuration"]
    print(f"Frozen {configuration['name']}; retraining through {metadata['windows']['test']['origin']}", flush=True)
    forecasts, details = train_predict(db, metadata["windows"]["test"], configuration,
                                      metadata, final, "test")
    event(directory, "final_model_trained", model_sha256=file_hash(final / "model.txt"))
    frozen_on_disk = read_json(directory / "freeze.json")
    require(frozen_on_disk["design"] == freeze and frozen_on_disk["sha256"] == digest(freeze),
            "Frozen design changed before test evaluation")
    write_json(marker, {"at": utc_now(), "freeze_sha256": digest(freeze),
                        "predictions_sha256": file_hash(final / "predictions.parquet")})
    event(directory, "test_evaluation_started", freeze_sha256=digest(freeze))
    forecasts = attach_actuals(db, forecasts)
    metrics = forecast_metrics(forecasts["actual_units"], forecasts["predicted_units"])
    forecasts.to_parquet(final / "evaluated.parquet", index=False)
    result = {"metrics": metrics, "details": details, "freeze_sha256": digest(freeze),
              "baseline": baseline_metrics(db, "test"), "evaluated_at": utc_now()}
    write_json(outcome, result)
    event(directory, "test_evaluation_completed", freeze_sha256=digest(freeze))
    return result


def run_model(output, artifacts, *, validation_only=False, training_days=730,
              validation_days=28, test_days=28, candidates=None):
    output, artifacts = Path(output), Path(artifacts)
    path = output / "gold/retailpulse.duckdb"
    require(path.is_file(), "Gold database must exist before modeling")
    with duckdb.connect(str(path)) as db:
        db.execute("SET memory_limit = '768MB'")
        db.execute("SET threads = 4")
        source, last_date = db.execute("SELECT gold_run_id, last_sales_date FROM pipeline_metadata").fetchone()
        windows = temporal_windows(last_date, validation_days, test_days)
        baseline = db.execute("SELECT windows_json FROM baseline_run").fetchone()
        require(baseline is not None, "Run RP-06 baselines before RP-07")
        import json

        baseline_windows = json.loads(baseline[0])
        for split, window in windows.items():
            require(baseline_windows[split]["training_end"] == window["origin"]
                    and baseline_windows[split]["evaluation_end"] == window["end"]
                    and baseline_windows[split]["evaluation_start"] == window["start"],
                    "Model windows must match the RP-06 baseline contract")
        plan = {"source_run_id": source, "windows": windows, "training_days": training_days,
                "candidates": candidates if candidates is not None else CANDIDATES,
                "implementation_sha256": implementation_hash(), "feature_version": FEATURE_VERSION,
                "model_environment": {name: version(name) for name in
                                      ("lightgbm", "numpy", "pandas", "duckdb")}}
        directory = artifacts / "rp07" / source
        directory.mkdir(parents=True, exist_ok=True)
        with exclusive_run(directory):
            plan_path = directory / "plan.json"
            if plan_path.exists():
                metadata = read_json(plan_path)
                require(metadata["plan_sha256"] == digest(plan),
                        "RP-07 plan is immutable for this Gold source; no post-test retuning")
            else:
                metadata = {**plan, "plan_sha256": digest(plan),
                            "created_at": utc_now(), "environment": environment(artifacts.parent),
                            "baseline_validation": baseline_metrics(db, "validation")}
                write_json(plan_path, metadata)
                event(directory, "plan_created", plan_sha256=metadata["plan_sha256"])
            complete = directory / "complete.json"
            if complete.exists():
                evidence = read_json(complete)
                freeze = read_json(directory / "freeze.json")
                require(digest(freeze["design"]) == freeze["sha256"] == evidence["freeze_sha256"],
                        "Frozen design checksum mismatch")
                for name, expected in evidence["artifact_hashes"].items():
                    require(file_hash(directory / name) == expected, f"Changed model artifact: {name}")
                if validation_only:
                    return {"status": "VALIDATION_FROZEN", "winner": freeze["design"],
                            "artifact_path": str(directory), "reused": True, "test_evaluated": False}
                persist_model(db, pd.read_parquet(directory / "forecasts.parquet"), evidence)
                return {**evidence, "reused": True}
            tracker = Tracking(artifacts / "mlflow")
            results, freeze = validation_search(db, metadata, directory, tracker)
            if validation_only:
                return {"status": "VALIDATION_FROZEN", "candidates": results, "winner": freeze,
                        "artifact_path": str(directory), "test_evaluated": False}
            test = final_evaluation(db, metadata, directory, freeze, tracker)
            final = directory / "final"
            run_file = final / "mlflow_run.json"
            if run_file.exists():
                run_id = read_json(run_file)["run_id"]
            else:
                run_id = tracker.log_run("frozen_final", freeze["configuration"], test["details"],
                                         test["metrics"], final, {**metadata, "freeze": freeze}, "test")
                write_json(run_file, {"run_id": run_id})
            validation = pd.read_parquet(directory / freeze["configuration"]["name"] / "evaluated.parquet")
            forecasts = pd.concat([validation, pd.read_parquet(final / "evaluated.parquet")], ignore_index=True)
            forecasts.to_parquet(directory / "forecasts.parquet", index=False)
            metrics = segmented_metrics(forecasts)
            metrics.to_csv(directory / "segmented_metrics.csv", index=False)
            baseline_segments = db.execute("SELECT * FROM forecast_evaluation WHERE model='rolling_mean' "
                                           "ORDER BY split, segment_type, segment").fetchdf()
            baseline_segments.to_csv(directory / "baseline_segments.csv", index=False)
            evidence = {"status": "COMPLETE", "source_run_id": source, "model": MODEL_NAME,
                        "freeze_sha256": digest(freeze), "winner": freeze, "candidates": results,
                        "test": test, "baseline_validation": metadata["baseline_validation"],
                        "final_run_id": run_id, "experiment": tracker.experiment_name,
                        "tracking_uri": tracker.uri, "artifact_path": str(directory),
                        "forecast_rows": len(forecasts), "evaluation_rows": len(metrics),
                        "artifact_hashes": {name: file_hash(directory / name) for name in
                                            ("forecasts.parquet", "final/model.txt", "final/categories.json",
                                             "segmented_metrics.csv", "baseline_segments.csv")}}
            persist_model(db, forecasts, evidence)
            event(directory, "gold_persisted", forecasts=len(forecasts), mlflow_run_id=run_id)
            write_json(complete, evidence)
            return {**evidence, "reused": False}
