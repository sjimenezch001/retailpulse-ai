from datetime import date

import duckdb
import pytest
from pydantic import ValidationError

from retailpulse.agent.contracts import ForecastRequest, KpiRequest
from retailpulse.agent.database import gold_session
from retailpulse.agent.errors import AgentError
from retailpulse.agent.tools import GoldTools


def kpi(metric="units", **kwargs):
    return KpiRequest(metric=metric, start_date=date(2020,1,1), end_date=date(2020,1,8), **kwargs)


@pytest.mark.parametrize("arguments", [
    {"metric": "secret_table"}, {"metric": "profit"}, {"metric": "units", "sql": "SELECT 1"},
    {"metric": "units", "store": "SYN_A'; DROP TABLE dim_store;--"},
    {"metric": "units", "limit": 101}, {"metric": "units", "limit": True},
    {"metric": "units", "limit": "1"}, {"metric": "units", "granularity": "item_id;SELECT"},
    {"metric": "units", "start_date": 1577836800},
])
def test_closed_kpi_contract(arguments):
    with pytest.raises(ValidationError):
        KpiRequest.model_validate({"start_date":"2020-01-01", "end_date":"2020-01-08", **arguments})


@pytest.mark.parametrize("arguments", [
    {"models": ["imaginary"]}, {"models": []}, {"models": ["rolling_mean"]*5},
    {"horizon": -1}, {"horizon": "7"}, {"split": "production"}, {"segmentation": "raw_rows"},
])
def test_closed_forecast_contract(arguments):
    with pytest.raises(ValidationError):
        ForecastRequest.model_validate({"split":"test", **arguments})


def test_revenue_null_and_weighted_rollups(agent_gold):
    tools = GoldTools(agent_gold)
    assert tools.get_kpi(kpi("revenue_proxy")).rows[0].value is None
    assert tools.get_kpi(kpi("known_revenue_proxy")).rows[0].value == 308
    assert tools.get_kpi(kpi("price_coverage")).rows[0].value == .875
    assert tools.get_kpi(kpi("rolling_7d")).rows[0].value == 4  # Per-day sum, never 32.
    assert tools.get_kpi(kpi("rolling_28d")).rows[0].value == 8
    assert tools.get_kpi(kpi("units", item="SYN_2", store="SYN_A")).rows[0].value == 80


def test_all_missing_prices_are_unknown_and_grains_reconcile(agent_gold):
    tools = GoldTools(agent_gold)
    for metric in ("revenue_proxy", "known_revenue_proxy"):
        result = tools.get_kpi(KpiRequest(metric=metric, start_date="2020-01-01", end_date="2020-01-01"))
        assert result.rows[0].value is None and result.rows[0].missing_observations == 4
    for grain, count in (("day", 8), ("week", 2), ("month", 1), ("department", 2)):
        rows = tools.get_kpi(kpi(granularity=grain)).rows
        assert len(rows) == count and sum(row.value for row in rows) == 176


def test_forecast_segment_totals_and_actuals_contract(agent_gold):
    tools = GoldTools(agent_gold)
    for segmentation in ("store", "department", "day", "horizon", "demand_level"):
        rows = tools.get_forecast(ForecastRequest(split="test", segmentation=segmentation)).rows
        assert sum(row.actual_units for row in rows) == 44
    with duckdb.connect(str(agent_gold)) as db:
        db.execute("UPDATE fact_forecast SET actual_units=1 WHERE split='future'")
    with pytest.raises(AgentError, match="inconsistent"):
        tools.get_forecast(ForecastRequest(models=("rolling_mean",), split="future"))


def test_forecasts_filters_no_double_count_and_future(agent_gold):
    tools = GoldTools(agent_gold)
    result = tools.get_forecast(ForecastRequest(models=("rolling_mean",), split="test", store="SYN_A", horizon=1))
    assert result.rows[0].WMAPE == pytest.approx(6/11)
    assert result.rows[0].WMAPE != pytest.approx((4/1+2/10)/2)
    assert result.rows[0].MAE == 3 and result.rows[0].RMSE == pytest.approx(10**.5)
    both = tools.get_forecast(ForecastRequest(models=("rolling_mean", "lightgbm_global_v1"), split="test"))
    assert len(both.rows) == 2 and {row.actual_units for row in both.rows} == {44}
    future = tools.get_forecast(ForecastRequest(models=("rolling_mean",), split="future"))
    assert future.rows[0].actual_units is None and future.rows[0].WMAPE is None
    with pytest.raises(AgentError, match="historical validation/test"):
        tools.get_forecast(ForecastRequest(models=("lightgbm_global_v1",), split="future"))


def test_zero_denominator_is_explicit(agent_gold):
    with duckdb.connect(str(agent_gold)) as db:
        db.execute("UPDATE fact_forecast SET actual_units=0 WHERE split='test'")
    row = GoldTools(agent_gold).get_forecast(ForecastRequest(split="test")).rows[0]
    assert row.WMAPE is None and row.wmape_zero_denominator
    assert row.MAE is not None and row.RMSE is not None


@pytest.mark.parametrize("kwargs", [{"store":"UNKNOWN"}, {"department":"UNKNOWN"}, {"item":"UNKNOWN"}, {"item":"SYN_1","department":"D2"}])
def test_filter_membership(agent_gold, kwargs):
    with pytest.raises(AgentError):
        GoldTools(agent_gold).get_kpi(kpi(**kwargs))


def test_row_limits_dates_and_missing_snapshot(agent_gold, tmp_path):
    with pytest.raises(AgentError, match="row limit"):
        GoldTools(agent_gold).get_kpi(kpi(granularity="day", limit=3))
    with pytest.raises(AgentError, match="observed only"):
        GoldTools(agent_gold).get_kpi(KpiRequest(metric="units",start_date="2030-01-01",end_date="2030-01-02"))
    with pytest.raises(AgentError, match="unavailable"):
        GoldTools(tmp_path / "absent.duckdb").get_kpi(kpi())
    with pytest.raises(ValidationError):
        KpiRequest(metric="data_freshness",store="SYN_A")


@pytest.mark.parametrize("mutation", ["UPDATE pipeline_metadata SET gold_run_id=NULL", "UPDATE fact_forecast SET source_run_id='stale'", "UPDATE fact_forecast SET actual_units=NULL WHERE split='test'"])
def test_provenance_and_observed_contract(agent_gold, mutation):
    with duckdb.connect(str(agent_gold)) as db:
        db.execute(mutation)
    with pytest.raises(AgentError):
        GoldTools(agent_gold).get_forecast(ForecastRequest(split="test"))


def test_connection_defense_in_depth(agent_gold, tmp_path):
    # These SQL statements are test-only probes, never exposed through agent interfaces.
    for sql in ("DROP TABLE dim_store", "CREATE TABLE forbidden(x INT)", "ATTACH ':memory:' AS other", "SET enable_external_access=true", "SELECT * FROM read_text('does-not-exist.env')"):
        with pytest.raises(AgentError), gold_session(agent_gold) as db:
            db.execute(sql)
    with gold_session(agent_gold) as db:
        assert db.execute("SELECT current_setting('enable_external_access'), current_setting('threads')").fetchone() == (False, 1)
    assert not (tmp_path / "forbidden").exists()


def test_deadline_interrupts_active_query(agent_gold):
    with pytest.raises(AgentError) as exc, gold_session(agent_gold, .02) as db:
        db.execute("SELECT sum(sin(i)) FROM range(10000000000) t(i)")
    assert exc.value.category == "query_timeout"


def test_forged_contract_revalidated(agent_gold):
    forged = kpi().model_copy(update={"metric":"units); DROP TABLE dim_store;--"})
    with pytest.raises(ValidationError):
        GoldTools(agent_gold).get_kpi(forged)
