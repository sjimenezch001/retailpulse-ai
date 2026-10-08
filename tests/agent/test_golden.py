from pathlib import Path

from retailpulse.agent.evaluation import evaluate

ROOT = Path(__file__).resolve().parents[2]


def test_golden_questions(assistant, agent_gold):
    report = evaluate(assistant, ROOT, agent_gold)
    assert report["total"] >= 25
    assert report["passing"] == report["total"], [r for r in report["results"] if not r["passed"]]
    assert report["numerical_grounding_accuracy"] == report["provenance_coverage"] == 1
    assert report["categories"]["numerical"] >= 10
