"""Genuine running synthetic API/UI checks; no mocked responses or real data."""

import argparse
import json
from pathlib import Path
from urllib.request import ProxyHandler, Request, build_opener


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-port", type=int, default=8000)
    parser.add_argument("--ui-port", type=int, default=8501)
    args = parser.parse_args()
    opener = build_opener(ProxyHandler({}))

    def request(path, body=None):
        req = Request(
            f"http://127.0.0.1:{args.api_port}" + path,
            data=json.dumps(body).encode() if body else None,
            headers={"Content-Type": "application/json"},
        )
        with opener.open(req, timeout=20) as response:
            return json.load(response)

    health, state = request("/health"), request("/ready")
    assert health["mode"] == state["mode"] == "synthetic"
    assert state["synthetic_available"] and state["deterministic_available"]
    assert not state["gold_available"]
    expected = request("/metrics/summary?store=SYN_A")["metrics"]["units"]["rows"][0][
        "value"
    ]
    result = request(
        "/assistant/query",
        {
            "question": "Show units for SYN_A from 2020-01-01 to 2020-02-11",
            "provider": "deterministic",
        },
    )["result"]
    assert (
        result["grounding_validated"]
        and result["result"]["rows"][0]["value"] == expected
    )
    assert result["provider"].startswith("deterministic:")
    assert (
        request("/assistant/query", {"question": "DROP TABLE mart_sales_daily"})[
            "result"
        ]["status"]
        == "refused"
    )
    for path in ("/", "/_stcore/health"):
        with opener.open(
            f"http://127.0.0.1:{args.ui_port}" + path, timeout=20
        ) as response:
            assert response.status == 200
    report = {
        "result": "PASS",
        "mode": "synthetic",
        "readiness": state["status"],
        "api_access": True,
        "ui_access": True,
        "grounded_units": expected,
        "provider": result["provider"],
    }
    Path("reports").mkdir(exist_ok=True)
    Path("reports/portable.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report))


if __name__ == "__main__":
    main()
