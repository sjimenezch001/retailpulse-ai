# RP-09 live Ollama diagnosis

The installed service reports **Ollama 0.40.0** and lists the existing
**qwen2.5:1.5b** model. No installation, model download, retraining or Gold
write was performed during this repair.

## Observed failures

| Layer | Observed result |
| --- | --- |
| Host connectivity before starting the service | Connection refused, Windows error 10061, on loopback port 11434 |
| Model discovery after starting the installed service | Success; version 0.40.0 and qwen2.5:1.5b confirmed |
| Original adapter, 10-second timeout | Timeout after 10,052.182 ms; no complete API response available for validation |
| Original prompt/schema with a 30-second budget | Successful genuine response in 5,306.175 ms; valid JSON/schema and exact scope match |
| Controlled cold-model request after timeout repair | Successful selection in 14,594 ms, including 7,115.4255 ms loading the model |
| First strict live golden run, original prompt | 33/36 accepted; three rejected model proposals fell back |

The cold request returned **25,307 units** for CA_1 during April 2016 and
reported `ollama:qwen2.5:1.5b`. Its result was independently checked against
Gold. The measured cold load plus generation exceeds the original timeout.
The service was started hidden on loopback using the installed executable;
starting the service is an operational prerequisite, not an automatic side
effect of the assistant.

The original prompt also exposed genuine model reliability failures in the
golden run. `units_by_store` changed store, department, item and comparison
arguments; `spikes` failed strict schema validation; `definition_rolling`
rewrote the documentation query. All were rejected. The
[initial live evaluation](rp09_live_initial_evaluation.json) preserves
**19 validated model calls, three fallback cases and 14 preflight outcomes**.
Its functional results were 36/36 because fallback retained correct answers;
its live validation result was **33/36 and FAIL**. These outcomes are not
reclassified as successful model calls.

## Repair and unchanged protections

The adapter's default chat timeout is now 30 seconds, within its existing
maximum. Discovery retains its two-second timeout. The selection prompt
explicitly asks for the application-validated candidate, preserving null
filters, identifiers, dates, grouping, comparison and limits, and copying
documentation queries verbatim. The model's role remains scope confirmation;
this repair does not claim general conversational intent recognition.

The full Pydantic schema, tool allowlists, request validation, exact candidate
equality, deterministic numerical renderer, parameterized SQL and DuckDB
read-only/resource protections are unchanged. The adapter does not silently
repair a changed proposal, relax validation or retry until a preferred result
appears. Complete API generation is required before validating its JSON.

Safe diagnostics distinguish connectivity, HTTP/API response, generation,
schema, scope and timeout failures. They expose fixed categories, numeric
timing/token metadata, validation error counts and known changed-field names.
They do not expose prompts, generated text, credentials, headers, HTTP bodies
or exception messages. Diagnostics appear in CLI output, typed answers,
ignored local traces and reviewed evaluation evidence.

Preflight refusals now report `deterministic:preflight`, with no model attempt.
Explicit `--provider ollama` rejects fallback as successful live validation:
both `ask` and `agent-eval` return nonzero when their requested live call falls
back. Evaluation records functional correctness separately from live success.

## Reproduction

Ensure Ollama is running with the existing model available, then execute:

```powershell
.\.venv\Scripts\python.exe -m retailpulse ask "How many units did CA_1 sell during April 2016?" --provider ollama --ollama-model qwen2.5:1.5b
.\.venv\Scripts\python.exe -m retailpulse agent-eval --provider ollama --ollama-model qwen2.5:1.5b
```

Check the explicit provider, per-case diagnostics and `live_llm_validated`.
The suite contains 22 routed cases, including two refusals after tool
selection, and 14 preflight cases that intentionally never call the model.
The [RP-09 gate](rp09_gate.md) records the final full rerun, regression checks,
latency, artifact integrity and gate decision.
