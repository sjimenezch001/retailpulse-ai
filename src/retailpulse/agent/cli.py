"""Thin local entry points; the assistant core has no CLI or HTTP dependency."""
import json

import duckdb

from retailpulse.agent.contracts import ProviderDiagnostic
from retailpulse.agent.errors import AgentError
from retailpulse.agent.evaluation import evaluate, write_evaluation
from retailpulse.agent.orchestrator import Assistant
from retailpulse.agent.provider import Ollama, ProviderError, detect_ollama
from retailpulse.agent.retrieval import DocSearch
from retailpulse.agent.tools import GoldTools


def create_assistant(settings, root, provider_mode="auto", model=None):
    provider = None
    discovery_diagnostic = None
    state = {"installed": None, "reachable": None, "models": [], "probe": "not_requested"}
    label = "deterministic:explicit_offline_mode"
    if provider_mode != "deterministic":
        state = detect_ollama()
        candidates = [name for name in state["models"] if "embed" not in name.casefold() and name.casefold().startswith(("llama", "qwen", "gemma", "phi", "mistral"))]
        selected = model or (sorted(candidates)[0] if candidates else None)
        if selected and selected in state["models"]:
            provider = Ollama(selected)
            label = "ollama:" + selected
        else:
            label = "deterministic_fallback:ollama_or_selected_model_unavailable"
            discovery_diagnostic = ProviderDiagnostic.model_validate(state["diagnostic"]) if "diagnostic" in state else ProviderError("model_unavailable").diagnostic
    assistant = Assistant(GoldTools(settings.output_path / "gold/retailpulse.duckdb"), DocSearch(root),
                          provider=provider, provider_status=label, discovery_diagnostic=discovery_diagnostic,
                          trace_path=root / "artifacts/agent/traces.jsonl")
    return assistant, state


def run(args, settings, root):
    assistant, state = create_assistant(settings, root, args.provider, args.ollama_model)
    if args.command == "ask":
        answer = assistant.ask(args.question)
        if args.json_output:
            print(answer.model_dump_json(indent=2))
        else:
            print(f"Provider: {answer.provider}\nStatus: {answer.status}\n{answer.answer}")
            print("Provider diagnostic: " + answer.provider_diagnostic.model_dump_json(exclude_none=True))
        live_failed = args.provider == "ollama" and answer.provider.startswith("deterministic_fallback:")
        return 1 if answer.status in ("unavailable", "error") or live_failed else 0
    try:
        def progress(record):
            print(f"{record['id']}: {'PASS' if record['passed'] else 'FAIL'}; {record['provider']}; {record['duration_ms']} ms", flush=True)
        result = evaluate(assistant, root, settings.output_path / "gold/retailpulse.duckdb",
                          require_live=args.provider == "ollama", progress=progress if args.provider == "ollama" else None)
    except (AgentError, duckdb.Error, OSError):
        print("Evaluation unavailable: check the local Gold snapshot and approved evaluation files.")
        return 1
    result["ollama"] = state
    target = root / "artifacts/agent/evaluation.json"
    write_evaluation(result, target)
    print(json.dumps({key:value for key,value in result.items() if key != "results"}, indent=2))
    print("Evaluation details: artifacts/agent/evaluation.json")
    return 0 if result["passing"] == result["total"] else 1
