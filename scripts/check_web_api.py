"""Opt-in real Gold acceptance. Requires the local RP-10 API and Ollama."""

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

import httpx

from retailpulse.agent.database import gold_session


def main():
    root = Path(__file__).resolve().parents[1]
    database = root / "data/processed/gold/retailpulse.duckdb"
    audit = json.loads((root / "docs/evidence/rp08_data_audit.json").read_text())
    protected = {
        database: audit["gold_sha256"],
        **{
            root / "artifacts/rp07/20f4dae75fff8e79204e" / name: sha
            for name, sha in audit["frozen_artifact_hashes"].items()
        },
    }

    def preserved():
        for path, expected in protected.items():
            with path.open("rb") as stream:
                assert hashlib.file_digest(stream, "sha256").hexdigest() == expected, (
                    path.name
                )

    preserved()
    report = {"checked_at": datetime.now(timezone.utc).isoformat(), "requests": {}}
    with httpx.Client(
        base_url="http://127.0.0.1:8000", trust_env=False, timeout=65
    ) as client:

        def get(name, path, params=None):
            start = perf_counter()
            response = client.get(path, params=params)
            response.raise_for_status()
            report["requests"][name] = {
                "http_status": response.status_code,
                "seconds": round(perf_counter() - start, 3),
            }
            return response.json()

        health = get("health", "/health")
        assert health["mode"] == "real" and health["dataset_available"]
        summary = get("summary", "/metrics/summary")
        scoped = get(
            "april_ca1",
            "/metrics/summary",
            {"store": "CA_1", "start_date": "2016-04-01", "end_date": "2016-04-30"},
        )
        forecasts = get("forecast", "/forecast")["result"]["rows"]
        with gold_session(database) as db:
            units, known_revenue, missing, spikes, coverage = db.execute(
                "SELECT sum(units), sum(units*sell_price), count(*) FILTER(WHERE sell_price IS NULL), sum(demand_spike_flag::INTEGER), avg((sell_price IS NOT NULL)::INTEGER) FROM mart_sales_daily"
            ).fetchone()
            april = db.execute(
                "SELECT sum(units) FROM mart_sales_daily WHERE store_id='CA_1' AND date BETWEEN DATE '2016-04-01' AND DATE '2016-04-30'"
            ).fetchone()[0]
        values = {
            metric: result["rows"][0]["value"]
            for metric, result in summary["metrics"].items()
        }
        assert values["units"] == units == 4530250
        assert math.isclose(values["known_revenue_proxy"], known_revenue, rel_tol=1e-10)
        assert values["demand_spike_flag"] == spikes
        assert math.isclose(values["price_coverage"], coverage)
        assert values["revenue_proxy"] is None
        assert (
            summary["metrics"]["revenue_proxy"]["rows"][0]["missing_observations"]
            == missing
        )
        assert scoped["metrics"]["units"]["rows"][0]["value"] == april == 25307
        for forecast in forecasts:
            expected = next(
                row
                for row in audit["forecast_metrics"]
                if row["model"] == forecast["model"] and row["split"] == "test"
            )
            for metric in ("WMAPE", "MAE", "RMSE"):
                assert math.isclose(forecast[metric], expected[metric], rel_tol=1e-10)
        for provider in ("deterministic", "ollama"):
            start = perf_counter()
            response = client.post(
                "/assistant/query",
                json={
                    "question": "How many units did CA_1 sell during April 2016?",
                    "provider": provider,
                },
            )
            response.raise_for_status()
            data = response.json()
            answer = data["result"]
            assert (
                answer["grounding_validated"]
                and answer["result"]["rows"][0]["value"] == april
            )
            if provider == "ollama":
                assert (
                    data["live_provider_succeeded"]
                    and answer["provider"] == "ollama:qwen2.5:1.5b"
                ), "Fallback is not live validation"
            else:
                assert (
                    not data["live_provider_succeeded"]
                    and answer["provider"] == "deterministic:explicit_offline_mode"
                )
            report["requests"][provider] = {
                "http_status": response.status_code,
                "seconds": round(perf_counter() - start, 3),
                "provider": answer["provider"],
                "request_id": answer["request_id"],
                "diagnostic": answer["provider_diagnostic"],
                "units": april,
                "grounding_validated": True,
            }
        invalid = client.get("/metrics/summary?sql=select+1")
        assert invalid.status_code == 422
        report["invalid_query_http_status"] = invalid.status_code
    preserved()
    report.update(
        result="PASS",
        dataset=health["dataset"],
        metrics=values,
        missing_price_observations=missing,
        forecast_metrics=forecasts,
        gold_sha256=audit["gold_sha256"],
        frozen_files_unchanged=45,
    )
    (root / "docs/evidence/rp10/real_api.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "result": report["result"],
                "requests": report["requests"],
                "protected_files": len(protected),
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
