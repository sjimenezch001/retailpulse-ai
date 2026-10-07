import pandas as pd
import pytest

from retailpulse.data.config import load_config
from retailpulse.data.source import (
    checksum,
    inspect_sources,
    price_coverage,
    profile_frame,
    read_sources,
    select_pilot,
)


def test_pending_manifest_has_no_fabricated_statistics(tmp_path):
    manifest = inspect_sources(tmp_path)
    assert manifest["status"] == "REAL-DATA VALIDATION PENDING"
    assert len(manifest["missing_files"]) == 3
    assert manifest["files"] == []


def test_inspection_reproducible_on_synthetic_files(fixture_dir):
    first = inspect_sources(fixture_dir)
    second = inspect_sources(fixture_dir)
    assert first["files"] == second["files"]
    assert first["files"][0]["sha256"] == checksum(fixture_dir / "calendar.csv")
    assert first["files"][2]["rows"] == 6
    assert first["files"][2]["columns"] == 48
    assert first["price_coverage"]["expected_keys"] == 36
    assert first["price_coverage"]["covered_keys"] == 35


def test_pilot_deterministic(sources):
    pilot = select_pilot(sources["sales"].sample(frac=1, random_state=1))
    assert pilot == {"stores": ["SYN_A", "SYN_B", "SYN_C"],
                     "departments": ["SYN_D1", "SYN_D2"]}


def test_missing_and_empty_input_rejected(tmp_path):
    with pytest.raises(ValueError, match="Missing or empty"):
        read_sources(tmp_path)
    (tmp_path / "calendar.csv").touch()
    with pytest.raises(ValueError, match="Missing or empty"):
        read_sources(tmp_path)


def test_profile_reports_problems_and_duplicates():
    frame = pd.DataFrame({"date": ["bad", "bad"], "d": ["d_1", "d_1"]})
    result = profile_frame("calendar", frame)
    assert result["duplicate_rows"] == 1
    assert result["date_range"]["invalid_dates"] == 2
    assert result["schema_problems"]


def test_duplicate_price_keys_rejected(sources):
    sources["prices"] = pd.concat([sources["prices"], sources["prices"].iloc[:1]])
    with pytest.raises(ValueError, match="Duplicate weekly"):
        price_coverage(sources)


def test_config_paths_and_empty_pilot(tmp_path):
    path = tmp_path / "config/local.yaml"
    path.parent.mkdir()
    path.write_text("dataset_path: data/raw/m5\noutput_path: data/processed\n")
    settings, root = load_config(path)
    assert settings.dataset_path == root / "data/raw/m5"
    assert settings.pilot.stores == []


def test_config_rejects_path_escape(tmp_path):
    path = tmp_path / "config/local.yaml"
    path.parent.mkdir()
    path.write_text("dataset_path: ../outside\noutput_path: data/processed\n")
    with pytest.raises(ValueError, match="inside the repository"):
        load_config(path)
