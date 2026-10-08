import signal
from types import SimpleNamespace

import pytest

from retailpulse.api import launcher
from retailpulse.api.client import ApiClient


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com",
        "http://user:secret@127.0.0.1",
        "http://127.0.0.1?url=remote",
        "http://localhost.evil",
    ],
)
def test_client_rejects_external_urls(url):
    with pytest.raises(ValueError):
        ApiClient(url)


def test_launcher_ready_and_interrupt_reaps_owned_children(
    tmp_path, monkeypatch, capsys
):
    children = []
    commands = []
    stopped = []
    monkeypatch.setattr(launcher, "free_port", lambda port: None)

    def popen(command, **kwargs):
        commands.append((command, kwargs))
        child = SimpleNamespace(poll=lambda: None)
        children.append(child)
        return child

    monkeypatch.setattr(launcher.subprocess, "Popen", popen)
    monkeypatch.setattr(launcher, "stop_children", lambda group: stopped.extend(group))
    monkeypatch.setattr(
        launcher.httpx.Client,
        "get",
        lambda *args: SimpleNamespace(
            status_code=200, json=lambda: {"dataset_available": True}
        ),
    )

    def interrupt(*args):
        raise KeyboardInterrupt

    monkeypatch.setattr(launcher.time, "sleep", interrupt)
    previous = signal.getsignal(signal.SIGTERM)
    assert (
        launcher.launch(
            SimpleNamespace(output_path=tmp_path),
            tmp_path,
            mode="synthetic",
            provider="deterministic",
        )
        == 0
    )
    assert children == stopped and len(stopped) == 2
    assert all(command[0] == launcher.sys.executable for command, _ in commands)
    assert commands[0][1]["env"]["RETAILPULSE_DEMO_MODE"] == "synthetic"
    assert "127.0.0.1" in commands[0][0]
    assert "Ready." in capsys.readouterr().out
    assert signal.getsignal(signal.SIGTERM) == previous


def test_launcher_partial_startup_failure_still_cleans_up(tmp_path, monkeypatch):
    children = []
    stopped = []
    monkeypatch.setattr(launcher, "free_port", lambda port: None)

    def popen(*args, **kwargs):
        if children:
            raise OSError("Second server failed")
        children.append(object())
        return children[0]

    monkeypatch.setattr(launcher.subprocess, "Popen", popen)
    monkeypatch.setattr(launcher, "stop_children", lambda group: stopped.extend(group))
    with pytest.raises(OSError):
        launcher.launch(SimpleNamespace(output_path=tmp_path), tmp_path)
    assert stopped == children


def test_launcher_rejects_same_port_before_starting(tmp_path):
    with pytest.raises(ValueError, match="differ"):
        launcher.launch(None, tmp_path, api_port=8501, ui_port=8501)
