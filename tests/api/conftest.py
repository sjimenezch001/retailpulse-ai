from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from retailpulse.api.app import create_app
from retailpulse.api.source import ApiSettings, portable_database


@pytest.fixture
def api(tmp_path, monkeypatch):
    monkeypatch.setattr("retailpulse.api.service.detect_ollama", lambda: {"models": []})
    database = portable_database(tmp_path / "snapshot")
    app = create_app(
        ApiSettings(tmp_path, database, mode="synthetic", provider="deterministic")
    )
    with TestClient(
        app, base_url="http://127.0.0.1", raise_server_exceptions=False
    ) as client:
        yield client


ROOT = Path(__file__).resolve().parents[2]
