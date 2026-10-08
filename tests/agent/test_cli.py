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
