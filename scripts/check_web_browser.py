"""Opt-in genuine browser acceptance; run against an already-started local demo."""

import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["real", "synthetic"], required=True)
    parser.add_argument(
        "--chrome", help="Optional installed Chromium/Chrome executable"
    )
    parser.add_argument("--port", type=int, default=8501)
    args = parser.parse_args()
    evidence = Path("docs/evidence/rp10")
    evidence.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=args.chrome)
        page = browser.new_page(viewport={"width": 1600, "height": 1400})
        page.set_default_timeout(65000)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(f"http://127.0.0.1:{args.port}")
        expect(page.get_by_role("heading", name="The demand picture")).to_be_visible()
        expect(page.get_by_test_id("stVegaLiteChart").first).to_be_visible()
        expect(page.get_by_test_id("stException")).to_have_count(0)
        if args.mode == "real":
            expect(page.get_by_text("4,530,250", exact=True)).to_be_visible()
            expect(page.get_by_text("3,790 days", exact=True).first).to_be_visible()
        else:
            expect(
                page.get_by_test_id("stAlertContentWarning").get_by_text(
                    "SYNTHETIC PORTFOLIO DEMO", exact=False
                )
            ).to_be_visible()
        page.screenshot(path=str(evidence / f"{args.mode}_overview.png"))
        page.get_by_role("tab", name="Forecast", exact=True).click()
        expect(
            page.get_by_text("Observed vs predicted demand", exact=True)
        ).to_be_visible()
        if args.mode == "real":
            expect(page.get_by_text("74.83%", exact=True)).to_be_visible()
            expect(page.get_by_text("79.48%", exact=True)).to_be_visible()
        page.screenshot(path=str(evidence / f"{args.mode}_forecast.png"))
        page.get_by_role("tab", name="Overview", exact=True).click()
        before = page.get_by_test_id("stMetricValue").first.inner_text()
        page.get_by_role("combobox", name="Store", exact=True).click()
        store = "CA_1" if args.mode == "real" else "SYN_A"
        page.get_by_role("option", name=store, exact=True).click()
        expect(page.get_by_test_id("stMetricValue").first).not_to_have_text(before)
        filtered = page.get_by_test_id("stMetricValue").first.inner_text()
        page.screenshot(path=str(evidence / f"{args.mode}_filtered.png"))
        page.get_by_role("tab", name="Ask RetailPulse", exact=True).click()
        page.get_by_role("button", name="Explore store demand", exact=True).click()
        expect(page.get_by_test_id("stChatMessage")).to_have_count(2, timeout=65000)
        if args.mode == "real":
            expect(page.get_by_text("Live local model", exact=False)).to_be_visible(
                timeout=65000
            )
            expect(
                page.get_by_text("units [all]: 25,307 units;", exact=False)
            ).to_be_visible()
        else:
            expect(
                page.get_by_text("deterministic:explicit_offline_mode", exact=False)
            ).to_be_visible()
        page.screenshot(path=str(evidence / f"{args.mode}_assistant.png"))
        page.get_by_role("tab", name="Architecture", exact=True).click()
        expect(
            page.get_by_text("Trace every answer back to its source", exact=True)
        ).to_be_visible()
        page.screenshot(path=str(evidence / f"{args.mode}_architecture.png"))
        assert not errors, errors
        expect(page.get_by_test_id("stException")).to_have_count(0)
        report = {
            "mode": args.mode,
            "tabs": 4,
            "store_filter": store,
            "units_before": before,
            "units_after": filtered,
            "forecast_comparison": "passed",
            "assistant": "ollama" if args.mode == "real" else "deterministic",
            "browser": browser.version,
            "page_errors": errors,
            "result": "PASS",
        }
        (evidence / f"{args.mode}_browser.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps(report), flush=True)
        browser.close()


if __name__ == "__main__":
    main()
