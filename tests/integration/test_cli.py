import json
import shutil
import subprocess
import sys
from pathlib import Path

import yaml


def test_full_synthetic_cli_pipeline(fixture_dir, tmp_path):
    # This entire project root is temporary; repository data and manifest are untouched.
    root = tmp_path / "synthetic_project"
    config = root / "config/local.yaml"
    config.parent.mkdir(parents=True)
    config.write_text(yaml.safe_dump({"dataset_path": "data/raw/m5", "output_path": "data/processed",
                                    "pilot": {"stores": ["SYN_A", "SYN_B", "SYN_C"],
                                              "departments": ["SYN_D1", "SYN_D2"]}}))
    shutil.copytree(fixture_dir, root / "data/raw/m5")
    shutil.copytree(Path(__file__).resolve().parents[2] / "sql", root / "sql")

    def run(*args):
        return subprocess.run([sys.executable, "-m", "retailpulse", "--config", str(config), *args],
                              capture_output=True, text=True, check=True, timeout=60)

    # No --sample: synthetic observations must never be labeled a real M5 sample.
    run("profile")
    manifest = json.loads((root / "data/contracts/raw_manifest.json").read_text())
    assert manifest["files"][2]["rows"] == 6
    assert not (root / "data/sample").exists()
    run("bronze")
    run("silver")
    run("gold", "--as-of", "2020-02-12")
    run("baseline", "--validation-days", "7", "--test-days", "7", "--future-horizon", "7")
    result = run("query", "03_forecast_errors")
    assert "WMAPE" in result.stdout
    assert "seasonal_naive_7" in result.stdout
    run("bronze")
    run("silver")
    run("gold", "--as-of", "2020-02-12")
    assert "seasonal_naive_7" in run("query", "03_forecast_errors").stdout


def test_cli_missing_bronze_source_fails(tmp_path):
    config = tmp_path / "config/local.yaml"
    config.parent.mkdir()
    config.write_text("dataset_path: data/raw/m5\noutput_path: data/processed\n")
    result = subprocess.run([sys.executable, "-m", "retailpulse", "--config", str(config), "bronze"],
                            capture_output=True, text=True, timeout=60)
    assert result.returncode != 0
    assert "Missing or empty required source" in result.stderr
    assert not (tmp_path / "data/processed/bronze/current.json").exists()
