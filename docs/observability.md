# Local observability

RP-11 preserves `/health` and adds `/ready`. Both are local, unauthenticated
endpoints subject to the existing Host, Origin, size and concurrency limits.

| Condition | `/health` | `/ready` |
| --- | --- | --- |
| Valid selected dataset and installed Ollama model | 200, `ok` | 200, `ready` |
| Valid dataset, optional Ollama unavailable | 200, `ok` | 200, `degraded`; deterministic available |
| Selected dataset missing or wrong mode | 200, `degraded` | 503, `unavailable`; no synthetic substitution |
| Four active requests already occupy the slots | 503, `busy` error | 503, `busy` error |

Readiness explicitly reports process/API reachability, selected mode, Gold,
synthetic, deterministic and Ollama availability. `gold_available` always means
real Gold. Readiness does not test a model generation: discovery has a five-second
cache, and live generation can still fail. The assistant discloses that fallback.
Liveness is the ability to obtain an HTTP response; an unavailable optional model
does not make a usable deterministic demo unready.

Startup permits 45 seconds for API/UI checks. Request bodies have a five-second
deadline and a 4096-byte limit; URL queries are limited to 2048 bytes. Four active
queries are allowed. DuckDB statements have the existing five-second interruption
budget, and summaries check an overall twelve-second budget between operations.
These are cooperative query budgets, not a promise of immediate thread cancellation.
Existing Ollama transport/generation bounds remain unchanged.

## JSON events

`retailpulse.events` writes one closed JSON object per event to stderr. The
launcher redirects child API output to ignored `artifacts/web_demo/<mode>/api.log`.
Launcher startup/shutdown events appear in its terminal; redirect stderr to an
ignored `.log` file if persistence is desired. Standard server lifecycle messages
may share the stream. HTTP access logging is disabled by the launcher.

| Field | Meaning |
| --- | --- |
| `timestamp` | UTC ISO timestamp |
| `request_id` | Generated UUID; incoming correlation headers are not trusted |
| `run_id` | Existing assistant trace UUID, when applicable |
| `component` | `api` or `launcher` |
| `event` | startup, shutdown, api_request, query, readiness, assistant or provider |
| `level`, `status` | Closed operational outcomes |
| `duration_ms` | Elapsed monotonic time, excluding queued requests |
| `mode` | real or synthetic |
| `source_version` | SHA-256 of the dataset version, not a local path |
| `operation`, `http_status` | Allowlisted endpoint operation and HTTP status |
| `error_category` | Allowlisted category; unknown categories become `other` |
| `tool`, `grounding_validated` | Approved selected tool and actual validation outcome |
| `provider_available` | Discovery outcome, not a successful generation claim |

No raw questions, URLs, headers, SQL parameters, responses, exception text or
credentials are logged. Unknown paths become `unknown`. HTTP errors include the
same generated `X-Request-ID` and return sanitized messages. The outer request
middleware suppresses unexpected exception tracebacks before they reach Uvicorn.

Agent trace files retain their contract but `validated_filters` is now empty by
default; user identifiers and date arguments are not persisted. Typed responses
still contain complete validated scope for the UI. Traces and logs are ignored.
The formatter also suppresses arbitrary unstructured messages and exception text.

On Windows, the launcher may terminate child processes before their ASGI lifespan
shutdown callbacks run. Its own shutdown event records completion of child cleanup;
the lifespan event is verified separately in portable tests. No claim of an API
shutdown callback is made when the OS terminated it abruptly.

See [sanitized actual event examples](evidence/rp11/log_examples.jsonl).
