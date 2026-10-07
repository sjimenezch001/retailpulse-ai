from datetime import date
from pathlib import Path

import duckdb
import pytest

from retailpulse.ingestion.bronze import ingest
from retailpulse.models.baseline import run_baselines
from retailpulse.quality.checks import QualityError
from retailpulse.transforms.gold import run_gold
from retailpulse.transforms.silver import run_silver


def test_baselines_gold_output_rerun_and_failure_preserves_results(fixture_dir, tmp_path):
    ingest(fixture_dir, tmp_path / "bronze")
    run_silver(tmp_path, ["SYN_A", "SYN_B", "SYN_C"], ["SYN_D1", "SYN_D2"])
    sql = Path(__file__).resolve().parents[2] / "sql"
    gold = run_gold(tmp_path, sql, date(2020, 2, 12))
    first = run_baselines(tmp_path, validation_days=7, test_days=7, future_horizon=7)
    second = run_baselines(tmp_path, validation_days=7, test_days=7, future_horizon=7)
    assert first == second
    assert first["forecast_rows"] == 6 * 7 * 3 * 3
    assert first["source_run_id"] == gold["gold_run_id"]
    with pytest.raises(QualityError, match="Insufficient history"):
        run_baselines(tmp_path)
    assert run_gold(tmp_path, sql, date(2020, 2, 12))["reused"]
    with duckdb.connect(str(tmp_path / "gold/retailpulse.duckdb"), read_only=True) as db:
        assert db.execute("SELECT count(*) FROM fact_forecast").fetchone()[0] == first["forecast_rows"]
        assert db.execute("SELECT count(*) FROM fact_forecast WHERE split='future' AND actual_units IS NOT NULL").fetchone() == (0,)
        assert db.execute("SELECT count(*) FROM fact_forecast WHERE training_end >= target_date").fetchone() == (0,)
        assert db.execute("SELECT count(*) FROM fact_forecast WHERE horizon != date_diff('day', forecast_origin, target_date)").fetchone() == (0,)
        assert not db.execute((sql / "queries/03_forecast_errors.sql").read_text()).fetchdf().empty
        assert db.execute("SELECT count(*) FROM baseline_run").fetchone() == (1,)
