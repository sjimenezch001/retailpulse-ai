"""Server-free local MLflow tracking and process memory observations."""
import hashlib
import json
import os
import subprocess
import sys
from importlib.metadata import distributions
from pathlib import Path
from threading import Event, Thread
from time import perf_counter

import psutil


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
                         encoding="utf-8")
    temporary.replace(path)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def file_hash(path):
    with Path(path).open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def environment(root):
    def git(*args):
        result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
        return result.stdout.strip() if result.returncode == 0 else "unavailable"
    return {"python": sys.version, "git_commit": git("rev-parse", "HEAD"),
            "git_dirty": bool(git("status", "--porcelain")),
            "dependencies": {dist.metadata["Name"]: dist.version for dist in distributions()}}


class Resources:
    """Sample this process RSS every 100 ms, including feature construction."""
    def __enter__(self):
        self.started = perf_counter()
        self.process = psutil.Process()
        self.peak = self.process.memory_info().rss
        self.stopped = Event()
        self.thread = Thread(target=self._sample, daemon=True)
        self.thread.start()
        return self

    def _sample(self):
        while not self.stopped.wait(0.1):
            self.peak = max(self.peak, self.process.memory_info().rss)

    def __exit__(self, *_):
        self.peak = max(self.peak, self.process.memory_info().rss)
        self.stopped.set()
        self.thread.join()
        self.seconds = perf_counter() - self.started

    def report(self):
        return {"runtime_seconds": self.seconds, "sampled_peak_rss_mib": self.peak / 2**20}


class Tracking:
    def __init__(self, root):
        # All metadata and artifacts remain local; no implicit tracking server.
        os.environ["MLFLOW_ENABLE_TELEMETRY"] = "false"
        os.environ["MLFLOW_DISABLE_AGENT_HINT"] = "1"
        from mlflow import MlflowClient

        path = Path(root).resolve()
        path.mkdir(parents=True, exist_ok=True)
        self.uri = "sqlite:///" + (path / "mlflow.db").as_posix()
        self.client = MlflowClient(tracking_uri=self.uri)
        self.experiment_name = "RetailPulse-RP07"
        experiment = self.client.get_experiment_by_name(self.experiment_name)
        self.experiment_id = experiment.experiment_id if experiment else self.client.create_experiment(
            self.experiment_name, artifact_location=(path / "artifacts").as_uri())

    def log_run(self, name, configuration, details, metrics, directory, metadata, split):
        run = self.client.create_run(self.experiment_id, tags={
            "mlflow.runName": name, "mlflow.source.git.commit": metadata["environment"]["git_commit"],
            "source_run_id": metadata["source_run_id"], "split": split,
            "selection_metric": "validation_WMAPE"})
        run_id = run.info.run_id
        try:
            parameters = {**configuration["params"], "rounds": configuration["rounds"],
                          "feature_set": configuration["feature_set"],
                          "training_start": details["training_start"], "training_end": details["training_end"],
                          "training_days": metadata["training_days"],
                          "validation_window": json.dumps(metadata["windows"]["validation"]),
                          "features": json.dumps(details["features"])}
            for key, value in parameters.items():
                self.client.log_param(run_id, key, value)
            for key in ("WMAPE", "MAE", "RMSE"):
                if metrics[key] is not None:
                    self.client.log_metric(run_id, f"{split}_{key}", metrics[key])
            for key in ("fit_seconds", "training_seconds", "runtime_seconds", "sampled_peak_rss_mib"):
                self.client.log_metric(run_id, key, details[key])
            self.client.log_dict(run_id, metadata, "metadata.json")
            self.client.log_dict(run_id, details, "training.json")
            # Native LightGBM format avoids an unnecessary scikit-learn dependency.
            for name in ("model.txt", "categories.json", "importance.csv"):
                self.client.log_artifact(run_id, str(Path(directory) / name))
            self.client.set_terminated(run_id)
        except Exception:
            self.client.set_terminated(run_id, status="FAILED")
            raise
        return run_id
