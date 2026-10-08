import asyncio
import hashlib
import os

import duckdb
import pytest

from retailpulse.agent.errors import AgentError
from retailpulse.api.app import RequestBounds
from retailpulse.api.source import ApiSettings, Source


def test_summary_filters_lineage_missing_price_and_read_only(api):
    path = api.app.state.service.settings.database
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    health = api.get("/health").json()
    assert health["dataset"]["mode"] == "synthetic"
    assert health["dataset"]["generation_timestamp"]
    response = api.get(
        "/metrics/summary",
        params={"store": "SYN_A", "start_date": "2020-01-01", "end_date": "2020-02-11"},
    )
    assert response.status_code == 200
    data = response.json()
    with duckdb.connect(str(path), read_only=True) as db:
        expected = db.execute(
            "SELECT sum(units), count(*) FILTER(WHERE sell_price IS NULL) FROM mart_sales_daily WHERE store_id='SYN_A'"
        ).fetchone()
    assert data["metrics"]["units"]["rows"][0]["value"] == expected[0]
    revenue = data["metrics"]["revenue_proxy"]["rows"][0]
    assert revenue["missing_observations"] == expected[1] > 0
    assert revenue["value"] is None
    assert data["metrics"]["known_revenue_proxy"]["rows"][0]["value"] > 0
    assert data["dataset"]["dataset_version"] == health["dataset"]["dataset_version"]
    assert {r["segment"] for r in data["stores"]["rows"]} == {"SYN_A"}
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before


def test_forecast_reconciles_independent_sql(api):
    data = api.get(
        "/forecast", params={"split": "test", "horizon": 1, "store": "SYN_A"}
    ).json()
    assert len(data["result"]["rows"]) == 2
    with duckdb.connect(
        str(api.app.state.service.settings.database), read_only=True
    ) as db:
        for row in data["result"]["rows"]:
            expected = db.execute(
                "SELECT sum(abs(actual_units-predicted_units))/sum(actual_units), avg(abs(actual_units-predicted_units)), sqrt(avg(pow(actual_units-predicted_units,2))) FROM fact_forecast WHERE split='test' AND horizon=1 AND store_id='SYN_A' AND model=?",
                [row["model"]],
            ).fetchone()
            assert [row[k] for k in ("WMAPE", "MAE", "RMSE")] == pytest.approx(expected)


@pytest.mark.parametrize(
    "path",
    [
        "/metrics/summary?sql=select+1",
        "/metrics/summary?store=CA_1%27",
        "/metrics/summary?start_date=2020-02-01",
        "/metrics/summary?start_date=2020-02-01&end_date=2020-01-01",
        "/metrics/summary?store=SYN_A&store=SYN_B",
        "/metrics/summary?database=secret.duckdb",
        "/forecast?model=unknown",
        "/forecast?models=unknown",
        "/forecast?horizon=0",
        "/forecast?limit=101",
        "/forecast?models=rolling_mean&models=rolling_mean",
        "/forecast?start_date=1234&end_date=5678",
    ],
)
def test_closed_query_validation(api, path):
    response = api.get(path)
    assert response.status_code == 422
    assert set(response.json()) == {"error"}
    assert response.json()["error"]["request_id"]
    assert "secret.duckdb" not in response.text


@pytest.mark.parametrize(
    "body",
    [
        {"question": "units", "sql": "select 1"},
        {"question": "units", "provider": "external"},
        {"question": True},
        {"question": "x" * 1001},
        {"question": "units", "tools": []},
    ],
)
def test_closed_body_validation(api, body):
    assert api.post("/assistant/query", json=body).status_code == 422


def test_payload_origin_host_query_bounds(api):
    assert (
        api.post(
            "/assistant/query",
            content="x" * 4097,
            headers={"Content-Type": "application/json"},
        ).status_code
        == 413
    )
    assert api.post("/assistant/query", content="question=x").status_code == 415
    assert api.get("/forecast?x=" + "a" * 2049).status_code == 414
    assert (
        api.get("/health", headers={"Origin": "https://attacker.example"}).status_code
        == 403
    )
    assert api.get("/health", headers={"Host": "attacker.example"}).status_code == 400
    assert api.request("GET", "/health", content="unexpected").status_code == 400


def test_chunked_body_limit_and_timeout():
    async def exercise(timeout=False):
        replies = []

        async def never_called(*args):
            pytest.fail("Rejected request reached the application")

        async def receive():
            if timeout:
                raise TimeoutError
            return {"type": "http.request", "body": b"x" * 3000, "more_body": True}

        async def send(message):
            replies.append(message)

        await RequestBounds(never_called, 8501)(
            {
                "type": "http",
                "method": "POST",
                "headers": [
                    (b"host", b"127.0.0.1"),
                    (b"content-type", b"application/json"),
                ],
            },
            receive,
            send,
        )
        return replies[0]["status"]

    assert asyncio.run(exercise()) == 413
    assert asyncio.run(exercise(True)) == 408


def test_cache_normalization_filters_and_invalidation(api):
    first = api.get("/metrics/summary").json()
    same = api.get("/metrics/summary?end_date=2020-02-11&start_date=2020-01-01").json()
    assert not first["cached"] and same["cached"]
    filtered = api.get("/metrics/summary?store=SYN_A").json()
    assert not filtered["cached"]
    assert filtered["metrics"]["units"] != first["metrics"]["units"]
    path = api.app.state.service.settings.database
    stat = path.stat()
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1000000000))
    changed = api.get("/metrics/summary").json()
    assert not changed["cached"]
    assert changed["dataset"]["dataset_version"] != first["dataset"]["dataset_version"]
    assert len(api.app.state.service.cache) == 1


def test_safe_errors_and_timeout(api, monkeypatch):
    service = api.app.state.service

    def timeout(*args):
        raise AgentError(
            "query_timeout", "The query exceeded its deadline.", "unavailable"
        )

    monkeypatch.setattr(service, "forecast", timeout)
    assert api.get("/forecast").status_code == 504

    def bug(*args):
        raise RuntimeError("secret-token private/path")

    monkeypatch.setattr(service, "forecast", bug)
    response = api.get("/forecast")
    assert response.status_code == 500
    assert "secret-token" not in response.text and "private/path" not in response.text


def test_missing_real_and_wrong_mode_never_substitute(api, tmp_path):
    service = api.app.state.service
    service.source = Source(
        ApiSettings(tmp_path, tmp_path / "missing.duckdb", mode="real")
    )
    health = api.get("/health").json()
    assert not health["dataset_available"] and health["dataset"] is None
    assert api.get("/metrics/summary").status_code == 503
    service.source = Source(
        ApiSettings(tmp_path, service.settings.database, mode="real")
    )
    assert api.get("/forecast").json()["error"]["code"] == "mode_mismatch"


def test_offline_and_unavailable_provider_provenance(api):
    question = "Show units for SYN_A from 2020-01-01 to 2020-02-11"
    for provider in ("deterministic", "ollama"):
        data = api.post(
            "/assistant/query", json={"question": question, "provider": provider}
        ).json()
        assert data["result"]["grounding_validated"]
        assert data["result"]["tool"] == "get_kpi"
        assert (
            data["result"]["result"]["provenance"]["gold_run_id"] == "synthetic-web-v1"
        )
        assert not data["live_provider_succeeded"]
        if provider == "ollama":
            assert data["result"]["provider"].startswith("deterministic_fallback:")
            assert (
                data["result"]["provider_diagnostic"]["category"] == "model_unavailable"
            )


def test_refusal_and_synthetic_document_isolation(api):
    response = api.post(
        "/assistant/query",
        json={
            "question": "Run SQL DROP TABLE mart_sales_daily",
            "provider": "deterministic",
        },
    ).json()
    assert response["result"]["status"] == "refused"
    response = api.post(
        "/assistant/query",
        json={"question": "What does revenue_proxy mean?", "provider": "deterministic"},
    ).json()
    assert response["dataset"]["mode"] == "synthetic"
    assert "25,307" not in str(response) and "20f4dae" not in str(response)
    assert response["result"]["tool"] == "search_metric_docs"


def test_date_department_filters_and_busy_limit(api):
    response = api.get(
        "/metrics/summary",
        params={
            "department": "SYN_D1",
            "start_date": "2020-01-02",
            "end_date": "2020-01-05",
        },
    ).json()
    with duckdb.connect(
        str(api.app.state.service.settings.database), read_only=True
    ) as db:
        expected = db.execute(
            "SELECT sum(units) FROM mart_sales_daily WHERE dept_id='SYN_D1' AND date BETWEEN DATE '2020-01-02' AND DATE '2020-01-05'"
        ).fetchone()[0]
    assert response["metrics"]["units"]["rows"][0]["value"] == expected
    assert len(response["daily_trend"]["rows"]) == 4
    slots = api.app.state.service.slots
    for _ in range(4):
        slots.acquire()
    try:
        assert api.get("/forecast").status_code == 503
    finally:
        for _ in range(4):
            slots.release()
