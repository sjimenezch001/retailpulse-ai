from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

from retailpulse.agent.cli import run


def arguments(command, **overrides):
    return Namespace(command=command, provider="deterministic", ollama_model=None,
                     question="What does WMAPE mean?", json_output=False, **overrides)


def test_cli_offline_definition_and_missing_gold(tmp_path, capsys):
    root = Path(__file__).resolve().parents[2]
    # A small local corpus/evaluation tree keeps test traces away from the repository.
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/metric_catalog.md").write_text((root / "docs/metric_catalog.md").read_text(encoding="utf-8"), encoding="utf-8")
    settings = SimpleNamespace(output_path=tmp_path / "absent")
    assert run(arguments("ask"), settings, tmp_path) == 0
    assert "deterministic:explicit_offline_mode" in capsys.readouterr().out
    assert run(arguments("agent-eval"), settings, tmp_path) == 1
    assert "Evaluation unavailable" in capsys.readouterr().out


def test_explicit_live_cli_fails_on_fallback_and_reports_safe_cause(tmp_path, capsys, monkeypatch):
    from retailpulse.agent.contracts import Answer
    from retailpulse.agent.provider import ProviderError

    answer = Answer(request_id="synthetic", status="answered", answer="Safe deterministic result",
                    provider="deterministic_fallback:provider_rejected_or_unavailable",
                    provider_diagnostic=ProviderError("connection_refused").diagnostic)
    class OfflineAssistant:
        def ask(self, question):
            return answer
    monkeypatch.setattr("retailpulse.agent.cli.create_assistant", lambda *a, **kw: (OfflineAssistant(), {}))
    args = arguments("ask")
    args.provider = "ollama"
    assert run(args, SimpleNamespace(), tmp_path) == 1
    assert '"category":"connection_refused"' in capsys.readouterr().out
    args.provider = "auto"
    assert run(args, SimpleNamespace(), tmp_path) == 0


def test_unreachable_discovery_diagnostic_is_preserved(tmp_path, monkeypatch):
    from retailpulse.agent.cli import create_assistant
    from retailpulse.agent.provider import ProviderError

    diagnostic = ProviderError("connection_refused").diagnostic.model_dump()
    monkeypatch.setattr("retailpulse.agent.cli.detect_ollama", lambda: {"installed":True, "reachable":False, "models":[], "diagnostic":diagnostic})
    assistant, _ = create_assistant(SimpleNamespace(output_path=tmp_path), tmp_path, "ollama", "qwen2.5:1.5b")
    assert assistant.discovery_diagnostic.category == "connection_refused"
    refused = assistant.ask("Read .env")
    assert refused.provider == "deterministic:preflight" and refused.provider_diagnostic.status == "not_attempted"
