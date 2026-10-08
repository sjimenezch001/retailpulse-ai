"""Portable launcher and safety tooling checks without Docker or external accounts."""

import importlib.util
import json
import logging
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from retailpulse.api import launcher, observability
from retailpulse.api.app import create_app

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("system", ["nt", "posix"])
def test_launcher_platform_flags_and_shutdown(tmp_path, monkeypatch, system):
    commands, stopped = [], []
    monkeypatch.setattr(launcher, "os", SimpleNamespace(name=system, environ={}))
    monkeypatch.setattr(
        launcher.subprocess, "CREATE_NO_WINDOW", 0x08000000, raising=False
    )
    monkeypatch.setattr(launcher, "free_port", lambda port: None)

    def popen(command, **kwargs):
        commands.append((command, kwargs))
        return SimpleNamespace(poll=lambda: None)

    monkeypatch.setattr(launcher.subprocess, "Popen", popen)
    monkeypatch.setattr(
        launcher, "stop_children", lambda children: stopped.extend(children)
    )
    monkeypatch.setattr(
        launcher.httpx.Client,
        "get",
        lambda *args: SimpleNamespace(
            status_code=200, json=lambda: {"dataset_available": True}
        ),
    )
    monkeypatch.setattr(
        launcher.time, "sleep", lambda _: (_ for _ in ()).throw(KeyboardInterrupt())
    )
    assert launcher.launch(SimpleNamespace(output_path=tmp_path), tmp_path) == 0
    assert len(stopped) == 2
    assert all(
        c[1]["creationflags"] == (0x08000000 if system == "nt" else 0) for c in commands
    )
    assert all("127.0.0.1" in c[0] for c in commands)


def test_container_cannot_enable_real_mode(tmp_path, monkeypatch):
    monkeypatch.setenv("RETAILPULSE_CONTAINER", "1")
    with pytest.raises(ValueError, match="synthetic"):
        launcher.launch(None, tmp_path, mode="real")


def test_launcher_failure_message_omits_private_exception(
    tmp_path, monkeypatch, capsys
):
    def fail(*args, **kwargs):
        raise OSError("PRIVATE_SENTINEL_903")

    monkeypatch.setattr(launcher, "launch", fail)
    args = SimpleNamespace(
        mode="synthetic", provider="deterministic", api_port=8000, ui_port=8501
    )
    assert launcher.run(args, None, tmp_path) == 1
    assert "PRIVATE_SENTINEL_903" not in capsys.readouterr().err


def test_lifespan_logs_startup_and_shutdown(api):
    events = []

    class Capture(logging.Handler):
        def emit(self, record):
            events.append(
                json.loads(observability.JSONFormatter().format(record))["event"]
            )

    handler = Capture()
    observability.LOGGER.addHandler(handler)
    try:
        with TestClient(
            create_app(api.app.state.service.settings), base_url="http://127.0.0.1"
        ) as client:
            assert client.get("/ready").status_code == 200
    finally:
        observability.LOGGER.removeHandler(handler)
    assert events[0] == "startup" and events[-1] == "shutdown"


def test_secret_scanner_detects_new_credential_in_any_tracked_file(
    tmp_path, monkeypatch
):
    spec = importlib.util.spec_from_file_location(
        "scan_secrets", ROOT / "scripts/scan_secrets.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".secrets.baseline").write_text('{"results": {}}')
    # Disposable, deliberately invalid token shape; never a real credential.
    token = "ghp_" + uuid4().hex + "Ab7q"
    (tmp_path / "unexpected.md").write_text('value = "' + token + '"')
    monkeypatch.setattr(
        module.subprocess, "check_output", lambda *a, **k: b"unexpected.md\0"
    )
    assert module.main() == 1
    report = (tmp_path / "reports/secrets.json").read_text()
    assert token not in report
    assert json.loads(report)["unreviewed_findings"][0]["file"] == "unexpected.md"
