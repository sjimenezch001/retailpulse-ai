"""Golden-question evaluation with independent aggregate SQL references."""
import json
import math
from collections import Counter
from datetime import timedelta
from pathlib import Path
from time import perf_counter

import duckdb
import yaml

from retailpulse.agent.contracts import ForecastRequest, KpiRequest
from retailpulse.agent.retrieval import DOCUMENTS


def context(database):
    with duckdb.connect(str(database), read_only=True) as db:
        start, end = db.execute("SELECT first_sales_date,last_sales_date FROM pipeline_metadata").fetchone()
        store = db.execute("SELECT min(store_id) FROM dim_store").fetchone()[0]
        item, department = db.execute("SELECT item_id,dept_id FROM dim_product ORDER BY item_id LIMIT 1").fetchone()
    half = min(28, ((end-start).days+1)//2)
    return {"start": str(start), "end": str(end), "recent_start": str(end-timedelta(days=half-1)),
            "store": store, "item": item, "department": department}


def substitute(value, values):
    if isinstance(value, str):
        return value.format_map(values)
    if isinstance(value, dict):
        return {key: substitute(item, values) for key, item in value.items()}
    if isinstance(value, list):
        return [substitute(item, values) for item in value]
    return value


def close(actual, expected):
    if actual is None or expected is None:
        return actual is expected
    return math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-8)


def verify_numerical(answer, expected, database):
    """The expected scope comes from YAML, never from the chosen tool's filters."""
    result = answer.result
    assert answer.grounding_validated and result.rows, "Supported numerical questions must produce grounded rows."
    request = (KpiRequest if expected["tool"] == "get_kpi" else ForecastRequest).model_validate(expected["arguments"])
    assert result.filters == request, "Tool arguments differ from the golden scope."
    with duckdb.connect(str(database), read_only=True) as db:
        source = db.execute("SELECT gold_run_id,first_sales_date,last_sales_date,as_of_date,generated_at,source_ingestion_ts FROM pipeline_metadata").fetchone()
        assert result.provenance.gold_run_id == source[0]
        assert result.provenance.data_freshness == (source[3]-source[2]).days
        assert result.provenance.generated_at == source[4] and result.provenance.source_ingestion_ts == source[5]
        assert str(source[0]) in answer.answer and "Filters:" in answer.answer
        if isinstance(request, KpiRequest):
            if request.metric == "data_freshness":
                assert result.rows[0].value == (source[3]-source[2]).days
                return
            where, params = "date BETWEEN ? AND ?", [request.start_date, request.end_date]
            for column, value in (("store_id", request.store), ("dept_id", request.department), ("item_id", request.item)):
                if value:
                    where += f" AND {column}=?"
                    params.append(value)
            for row in result.rows:
                row_where, row_params = where, list(params)
                if request.granularity in ("store", "department"):
                    row_where += " AND " + {"store": "store_id", "department": "dept_id"}[request.granularity] + "=?"
                    row_params.append(row.segment)
                base = " FROM mart_sales_daily WHERE " + row_where
                units, revenue, n, prices, spikes, lo, hi = db.execute("SELECT sum(units),sum(revenue_proxy),count(*),count(sell_price),count(*) FILTER(WHERE demand_spike_flag),min(date)::DATE,max(date)::DATE" + base, row_params).fetchone()
                assert row.period.start == lo and row.period.end == hi, "Returned dates differ from the independent Gold period."
                assert row.observations == n, "Observation count differs from Gold."
                value = {"units": units, "revenue_proxy": revenue if n == prices else None,
                         "known_revenue_proxy": revenue, "price_coverage": prices/n,
                         "demand_spike_flag": spikes}.get(request.metric)
                if request.metric in ("rolling_7d", "rolling_28d"):
                    # Independent averaging over the canonical per-date sums.
                    sums = [r[0] for r in db.execute("SELECT sum(" + request.metric + ")" + base + " GROUP BY date", row_params).fetchall() if r[0] is not None]
                    value = sum(sums)/len(sums) if sums else None
                assert close(row.value, value), "KPI does not match independent Gold SQL."
                if request.comparison:
                    length = (request.end_date-request.start_date).days+1
                    previous_params = [request.start_date-timedelta(days=length), request.start_date-timedelta(days=1), *row_params[2:]]
                    previous = db.execute("SELECT sum(units)" + base, previous_params).fetchone()[0]
                    assert close(row.previous_value, previous) and close(row.change, value-previous)
                    assert close(row.change_pct, (value-previous)/previous if previous else None)
        else:
            assert {r.model for r in result.rows} == set(request.models)
            for row in result.rows:
                # Golden forecast cases deliberately compare the canonical overall evaluation table.
                total = db.execute("SELECT sum(predicted_units),sum(actual_units),count(*),min(target_date),max(target_date) FROM fact_forecast WHERE model=? AND split=?", [row.model, request.split]).fetchone()
                assert close(row.predicted_units, total[0]) and close(row.actual_units, total[1])
                assert row.observations == total[2] and row.period.start == total[3] and row.period.end == total[4]
                if request.split == "future":
                    assert row.WMAPE is None and row.MAE is None and row.RMSE is None
                else:
                    metrics = db.execute("SELECT WMAPE,MAE,RMSE FROM forecast_evaluation WHERE model=? AND split=? AND segment_type='overall'", [row.model, request.split]).fetchone()
                    assert all(close(a,b) for a,b in zip((row.WMAPE,row.MAE,row.RMSE),metrics,strict=True))


def verify_answer(answer, expected, root, database):
    assert answer.status == expected["status"], f"Expected {expected['status']}, got {answer.status}/{answer.error_category}"
    if "tool" in expected:
        assert answer.tool == expected["tool"], "Wrong tool selected."
    if "error" in expected:
        assert answer.error_category == expected["error"], "Wrong limitation or refusal."
    for phrase in expected.get("contains", []):
        assert phrase.casefold() in answer.answer.casefold(), "Required explanation is missing."
    if expected.get("tool") in ("get_kpi", "get_forecast"):
        verify_numerical(answer, expected, database)
    elif expected.get("tool") == "search_metric_docs":
        assert answer.grounding_validated and answer.result.excerpts
        for excerpt in answer.result.excerpts:
            assert excerpt.source_document in DOCUMENTS
            lines = (Path(root)/excerpt.source_document).read_text(encoding="utf-8-sig").splitlines()
            assert excerpt.excerpt == "\n".join(lines[excerpt.start_line-1:excerpt.end_line])
            assert f"{excerpt.source_document}:{excerpt.start_line}-{excerpt.end_line}" in answer.answer


def evaluate(assistant, root, database):
    root, database = Path(root), Path(database)
    document = yaml.safe_load((root/"tests/agent/golden_questions.yaml").read_text(encoding="utf-8"))
    values = context(database)
    records = []
    for original in document["questions"]:
        case = substitute(original, values)
        started = perf_counter()
        answer = assistant.ask(case["question"])
        try:
            verify_answer(answer, case["expected"], root, database)
            passed, reason = True, None
        except AssertionError as exc:
            passed, reason = False, str(exc)
        records.append({"id": case["id"], "category": case["category"], "passed": passed,
                        "outcome": answer.status, "tool": answer.tool, "provider": answer.provider,
                        "grounding_validated": answer.grounding_validated, "error_category": answer.error_category,
                        "duration_ms": round((perf_counter()-started)*1000, 3), "failure": reason})
    numerical = [r for r in records if r["category"] == "numerical"]
    latencies = sorted(r["duration_ms"] for r in records)
    return {"total": len(records), "passing": sum(r["passed"] for r in records),
            "categories": dict(Counter(r["category"] for r in records)),
            "answered": sum(r["outcome"] == "answered" for r in records),
            "safe_refusals_or_clarifications": sum(r["passed"] and r["outcome"] in ("refused", "clarification") for r in records),
            "numerical_grounding_accuracy": sum(r["passed"] for r in numerical)/len(numerical),
            "provenance_coverage": sum(r["grounding_validated"] for r in numerical)/len(numerical),
            "latency_ms": {"median": latencies[len(latencies)//2], "max": max(latencies)}, "results": records}


def write_evaluation(result, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
