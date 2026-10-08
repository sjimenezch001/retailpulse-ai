from pathlib import Path

from streamlit.testing.v1 import AppTest

from retailpulse.api.client import ApiClient, ApiClientError

APP = Path(__file__).resolve().parents[2] / "app/streamlit_app.py"


def test_four_tabs_filters_forecast_and_offline_chat(api, monkeypatch):
    calls = []

    def request(self, path, params=None, body=None):
        calls.append((path, params, body))
        response = api.post(path, json=body) if body else api.get(path, params=params)
        assert response.status_code == 200, response.text
        return response.json()

    monkeypatch.setattr(ApiClient, "request", request)
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not app.exception
    assert [tab.label for tab in app.tabs] == [
        "Overview",
        "Forecast",
        "Ask RetailPulse",
        "Architecture",
    ]
    assert any("SYNTHETIC PORTFOLIO DEMO" in w.value for w in app.warning)
    before = app.metric[0].value
    app.selectbox(key="store").select("SYN_A").run()
    assert not app.exception
    assert app.metric[0].value != before
    assert any(
        path == "/forecast" and ("store", "SYN_A") in params
        for path, params, _ in calls
        if params
    )
    app.chat_input[0].set_value(
        "Show units for SYN_A from 2020-01-01 to 2020-02-11"
    ).run()
    assert not app.exception
    assert len(app.chat_message) == 2
    assert any("deterministic:explicit_offline_mode" in c.value for c in app.caption)
    assert len(app.session_state["rp_chat"]) == 1
    app.radio[0].set_value("ollama").run()
    app.chat_input[0].set_value(
        "Show units for SYN_A from 2020-01-01 to 2020-02-11"
    ).run()
    assert not app.exception
    assert any("Deterministic fallback" in w.value for w in app.warning)
    assert not app.success


def test_ui_missing_api_has_actionable_error(monkeypatch):
    def unavailable(*args, **kwargs):
        raise ApiClientError("The local API is unavailable or timed out.")

    monkeypatch.setattr(ApiClient, "request", unavailable)
    app = AppTest.from_file(str(APP)).run()
    assert not app.exception
    assert "unavailable" in app.error[0].value
    assert "python -m retailpulse demo" in app.code[0].value


def test_ui_missing_gold_offers_explicit_synthetic_mode(api, monkeypatch):
    health = api.get("/health").json()
    health.update(
        dataset=None,
        dataset_available=False,
        status="degraded",
        message="Real Gold is unavailable.",
    )
    monkeypatch.setattr(ApiClient, "request", lambda *a, **kw: health)
    app = AppTest.from_file(str(APP)).run()
    assert not app.exception and not app.metric
    assert "--mode synthetic" in app.code[0].value
