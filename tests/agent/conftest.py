"""Extend a generated synthetic Gold fixture without changing earlier-stage tests."""
import pytest
from tests.test_bi import bi_gold as bi_gold
from tests.test_bi import connect

from retailpulse.agent.orchestrator import Assistant
from retailpulse.agent.retrieval import DocSearch
from retailpulse.agent.tools import GoldTools


@pytest.fixture
def agent_gold(bi_gold):
    with connect(bi_gold) as db:
        db.execute("ALTER TABLE mart_sales_daily ALTER date TYPE TIMESTAMP")
        db.execute("ALTER TABLE pipeline_metadata ADD source_ingestion_ts VARCHAR DEFAULT '2020-01-10T00:00:00+00:00'")
        db.execute("ALTER TABLE pipeline_metadata ADD generated_at VARCHAR DEFAULT '2020-01-10T01:00:00+00:00'")
        db.execute("ALTER TABLE fact_forecast ADD dept_id VARCHAR")
        db.execute("UPDATE fact_forecast SET dept_id=p.dept_id FROM dim_product p WHERE fact_forecast.item_id=p.item_id")
        db.execute("CREATE TABLE metric_definitions AS SELECT unnest(['units','revenue_proxy','rolling_7d','rolling_28d','demand_spike_flag','data_freshness']) metric")
    return bi_gold / "gold/retailpulse.duckdb"


@pytest.fixture
def assistant(agent_gold, tmp_path):
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    return Assistant(GoldTools(agent_gold), DocSearch(root), trace_path=tmp_path / "traces.jsonl")
