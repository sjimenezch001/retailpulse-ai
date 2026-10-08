"""Opt-in live UI acceptance. No model responses are invented or substituted."""

import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8503)
    parser.add_argument("--chrome", required=True)
    args = parser.parse_args()
    output = Path("docs/evidence/rp10_ui")
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=args.chrome)
        page = browser.new_page(viewport={"width": 1600, "height": 1500})
        page.set_default_timeout(65000)
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(f"http://127.0.0.1:{args.port}")
        expect(page.get_by_text("4,530,250", exact=True)).to_be_visible(timeout=30000)
        expect(page.get_by_test_id("stVegaLiteChart").first).to_be_visible()

        def select(label, option):
            page.get_by_role("combobox", name=label, exact=True).click()
            page.get_by_role("option", name=option, exact=True).click()

        def capture(name):
            expect(page.get_by_test_id("stStatusWidget")).not_to_be_visible(
                timeout=65000
            )
            expect(page.get_by_test_id("stException")).to_have_count(0)
            page.get_by_test_id("stMain").evaluate("e=>e.scrollTop=0")
            clipped = (
                page.get_by_test_id("stMetricValue")
                .locator("p")
                .evaluate_all(
                    "nodes=>nodes.filter(e=>e.getBoundingClientRect().width>0 && e.scrollWidth>e.clientWidth+1).map(e=>e.textContent)"
                )
            )
            assert not clipped, clipped
            caption_opacity = page.get_by_test_id("stCaptionContainer").first.evaluate(
                "e=>getComputedStyle(e).opacity"
            )
            assert caption_opacity == "1", caption_opacity
            if "dark" in name:
                colors = page.get_by_role(
                    "combobox", name="Tema" if "es" in name else "Theme", exact=True
                ).evaluate(
                    "e=>({fg:getComputedStyle(e).color,bg:getComputedStyle(e).backgroundColor,button:getComputedStyle(e.parentElement.querySelector('button[aria-haspopup]')).backgroundColor})"
                )
                assert (
                    colors["fg"] == "rgb(242, 243, 245)"
                    and colors["bg"] == "rgb(26, 28, 31)"
                    and colors["button"] == colors["bg"]
                ), colors
            page.screenshot(path=str(output / name))

        capture("overview_light_en.png")
        select("Language / Idioma", "Español")
        expect(page.get_by_role("tab", name="Resumen", exact=True)).to_be_visible()
        select("Tema", "Oscuro")
        expect(page.get_by_role("combobox", name="Tema", exact=True)).to_have_value(
            "Oscuro"
        )
        page.wait_for_function(
            "getComputedStyle(document.querySelector('[data-testid=stAppViewContainer]')).backgroundColor==='rgb(17, 18, 20)'"
        )
        expect(page.get_by_text("4.530.250", exact=True)).to_be_visible()
        capture("overview_dark_es.png")
        page.get_by_role("tab", name="Pronóstico", exact=True).click()
        expect(page.get_by_text("74,83%", exact=True)).to_be_visible()
        expect(page.get_by_text("79,48%", exact=True)).to_be_visible()
        capture("forecast_dark_es.png")
        page.get_by_role("tab", name="Pregúntale a RetailPulse", exact=True).click()
        expect(
            page.get_by_role("radio", name="Ollama · modelo local", exact=True)
        ).to_be_checked()
        select("Tema", "Claro")
        page.get_by_role("tab", name="Pregúntale a RetailPulse", exact=True).click()
        page.get_by_role(
            "button", name="Consultar demanda por tienda", exact=True
        ).click()
        expect(
            page.get_by_text(
                "La tienda CA_1 vendió 25.307 unidades durante abril de 2016.",
                exact=True,
            )
        ).to_be_visible(timeout=65000)
        expect(page.get_by_text("Modelo local en vivo", exact=False)).to_be_visible()
        capture("assistant_light_es.png")
        select("Tema", "Oscuro")
        select("Language / Idioma", "English")
        page.get_by_role("tab", name="Ask RetailPulse", exact=True).click()
        expect(page.get_by_role("combobox", name="Theme", exact=True)).to_have_value(
            "Dark"
        )
        expect(
            page.get_by_role("radio", name="Ollama · local model", exact=True)
        ).to_be_checked()
        expect(
            page.get_by_text(
                "Store CA_1 sold 25,307 units during April 2016.", exact=True
            )
        ).to_be_visible()
        expect(page.get_by_text("Live local model", exact=False)).to_be_visible()
        capture("assistant_dark_en.png")
        page.get_by_role("tab", name="Architecture", exact=True).click()
        expect(page.locator(".rp-stage")).to_have_count(4)
        capture("architecture_dark_en.png")
        page.get_by_role("tab", name="Overview", exact=True).click()
        page.set_viewport_size({"width": 760, "height": 1100})
        capture("overview_compact_dark_en.png")
        overflow = page.evaluate(
            "document.documentElement.scrollWidth > window.innerWidth"
        )
        assert not overflow
        independent = browser.new_page(viewport={"width": 1400, "height": 1100})
        independent.goto(f"http://127.0.0.1:{args.port}")
        expect(
            independent.get_by_role("combobox", name="Theme", exact=True)
        ).to_have_value("Light", timeout=30000)
        expect(
            independent.get_by_role("combobox", name="Language / Idioma", exact=True)
        ).to_have_value("English")
        assert not errors, errors
        report = {
            "result": "PASS",
            "browser": browser.version,
            "page_errors": errors,
            "same_session_language_and_theme_switches": "PASS",
            "independent_session_defaults": "PASS",
            "compact_horizontal_overflow": overflow,
            "live_spanish_question": "ollama:qwen2.5:1.5b",
            "answer_units": 25307,
            "answer_after_language_switch_units": 25307,
            "screenshots": [f.name for f in output.glob("*.png")],
        }
        (output / "browser.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps(report), flush=True)
        browser.close()


if __name__ == "__main__":
    main()
