import pandas as pd
import pytest

from retailpulse.data.snapshots import read_snapshot
from retailpulse.ingestion.bronze import ingest
from retailpulse.quality.checks import QualityError
from retailpulse.transforms.silver import run_silver


def test_bronze_to_silver_reconciliation_and_rerun(fixture_dir, tmp_path):
    bronze = ingest(fixture_dir, tmp_path / "bronze")
    first = run_silver(tmp_path, ["SYN_A", "SYN_B", "SYN_C"], ["SYN_D1", "SYN_D2"])
    tables, summary = read_snapshot(tmp_path / "silver")
    second = run_silver(tmp_path, ["SYN_C", "SYN_A", "SYN_B"], ["SYN_D2", "SYN_D1"])
    assert first == second
    assert summary["identity"]["bronze_run_id"] == bronze["pipeline_run_id"]
    assert summary["metrics"]["sales_rows"] == 252
    fact = tables["fact_sales_daily"]
    assert fact["pipeline_run_id"].unique().tolist() == [bronze["pipeline_run_id"]]
    assert fact["units"].sum() == summary["metrics"]["units"]
    again, _ = read_snapshot(tmp_path / "silver")
    pd.testing.assert_frame_equal(fact, again["fact_sales_daily"])
    pointer = (tmp_path / "silver/current.json").read_bytes()
    with pytest.raises(QualityError):
        run_silver(tmp_path, ["UNKNOWN"], ["SYN_D1"])
    assert pointer == (tmp_path / "silver/current.json").read_bytes()
