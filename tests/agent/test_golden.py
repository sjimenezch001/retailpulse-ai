from pathlib import Path

from retailpulse.agent.evaluation import evaluate

ROOT = Path(__file__).resolve().parents[2]


def test_golden_questions(assistant, agent_gold):
    report = evaluate(assistant, ROOT, agent_gold)
    assert report["total"] >= 25
    assert report["passing"] == report["total"], [r for r in report["results"] if not r["passed"]]
    assert report["numerical_grounding_accuracy"] == report["provenance_coverage"] == 1
    assert report["categories"]["numerical"] >= 10


def test_live_gate_never_counts_fallback_as_model_validation(assistant, agent_gold):
    from retailpulse.agent.provider import ProviderError

    class Offline:
        model = "mock"
        def select(self, *args):
            raise ProviderError("timeout")
    assistant.provider = Offline()
    report = evaluate(assistant, ROOT, agent_gold, require_live=True)
    assert report["functional_passing"] == 36
    assert report["passing"] == report["live_model"]["preflight_cases"] < 36
    assert report["live_model"]["validated_cases"] == 0
    assert report["live_model"]["fallback_cases"] == report["live_model"]["required_cases"]
    assert not report["live_llm_validated"] and report["live_latency_ms"] is None
