import shutil

import pandas as pd
import pytest

from retailpulse.ingestion.bronze import ingest, read_bronze


def test_idempotency_counts_and_traceability(fixture_dir, tmp_path, sources):
    output = tmp_path / "bronze"
    first = ingest(fixture_dir, output)
    frames, summary = read_bronze(output)
    second = ingest(fixture_dir, output)
    assert first["pipeline_run_id"] == second["pipeline_run_id"]
    assert not first["reused"] and second["reused"]
    assert len(list((output / "runs").iterdir())) == 1
    for name, frame in frames.items():
        assert len(frame) == len(sources[name])
        assert frame["source_checksum"].nunique() == 1
        assert frame["pipeline_run_id"].unique().tolist() == [summary["pipeline_run_id"]]
        pd.testing.assert_frame_equal(frame[sources[name].columns], sources[name])
        assert summary["tables"][name]["input_rows"] == summary["tables"][name]["output_rows"]


def test_changed_source_creates_new_snapshot(fixture_dir, tmp_path):
    raw, output = tmp_path / "raw", tmp_path / "bronze"
    shutil.copytree(fixture_dir, raw)
    first = ingest(raw, output)
    path = raw / "sales_train_evaluation.csv"
    frame = pd.read_csv(path)
    frame.loc[0, "d_1"] += 1
    frame.to_csv(path, index=False)
    second = ingest(raw, output)
    assert first["pipeline_run_id"] != second["pipeline_run_id"]
    assert len(list((output / "runs").iterdir())) == 2
    actual, _ = read_bronze(output)
    assert actual["sales"].iloc[0]["d_1"] == frame.iloc[0]["d_1"]


@pytest.mark.parametrize("content", ["", "date,wm_yr_wk,d\n", "wrong\nvalue\n"])
def test_invalid_input_does_not_publish(fixture_dir, tmp_path, content):
    raw, output = tmp_path / "raw", tmp_path / "bronze"
    shutil.copytree(fixture_dir, raw)
    (raw / "calendar.csv").write_text(content)
    with pytest.raises(ValueError):
        ingest(raw, output)
    assert not (output / "current.json").exists()


def test_missing_input_rejected(tmp_path):
    with pytest.raises(ValueError, match="Missing or empty"):
        ingest(tmp_path, tmp_path / "out")


def test_corrupt_output_not_silently_reused(fixture_dir, tmp_path):
    result = ingest(fixture_dir, tmp_path)
    path = tmp_path / "runs" / result["pipeline_run_id"] / "sales.parquet"
    path.write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="checksum mismatch"):
        ingest(fixture_dir, tmp_path)
