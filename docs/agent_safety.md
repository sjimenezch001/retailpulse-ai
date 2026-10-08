# Grounded assistant safety contract

RP-09 adds three approved tools and a stateless local orchestrator. Business
figures come from the existing Gold snapshot. No model generates SQL or
numerical answer text. Existing transformations, forecast results and
dependency versions were unchanged by RP-09. RP-10 now exposes this same core
through local HTTP endpoints; see [API contracts](api_examples.md).

## Trust boundaries

Questions, provider responses and retrieved documents are untrusted input.
Application configuration selects the database and repository root; neither
is a tool argument. The dispatcher exposes only `get_kpi`, `get_forecast`
and `search_metric_docs`. Pydantic contracts forbid unknown properties, unsafe
identifiers, unapproved metrics/models, coerced numeric limits and invalid
calendar ranges. Tool entry points revalidate even constructed request objects.
Identifiers are checked against Gold dimensions, including item/department
compatibility. Values are SQL parameters, never interpolated into SQL.

The English router supports a bounded set of explicit question patterns.
It refuses SQL, commands, secrets, raw dumps and instruction bypasses.
Unsupported conditions and ambiguous scope request clarification. These
language checks supplement the closed tool interfaces; they are not the
database security boundary. There is no arbitrary SQL or filesystem tool.
The host process, application code and configured database remain trusted;
this is not an operating-system sandbox for someone who can edit the program.

## Read-only query contract

Each numerical call opens and closes DuckDB with `read_only=True` and the
following locked configuration:

| Control | Value |
| --- | --- |
| External file/network access | `enable_external_access=false` |
| Extension auto-install/load | Both disabled |
| Configuration changes | `lock_configuration=true` |
| Execution threads | 1 |
| DuckDB memory budget | 256 MB |
| Temporary spill budget | 0 B |
| Cumulative SQL execution deadline per session | 5 seconds by default; maximum 10 |
| Aggregate response rows | 100 maximum; overflow rejected, never silently truncated |
| Selected date interval | At most 3,661 days, inside observed or forecast bounds |

A timer interrupts active SQL when the session deadline expires. Exhausted
time/memory, absent Gold, schema failures and incomplete provenance produce
sanitized unavailable responses. The memory setting is DuckDB's internal
budget, not a hard process-wide RAM limit. The deadline covers SQL execution,
not Python startup or database opening. Tests also attempt forbidden writes,
ATTACH, external reads and configuration changes directly on a secured session.
These controls follow the [DuckDB security guidance](https://duckdb.org/docs/current/operations_manual/securing_duckdb/overview).

Only developer-owned SQL fragments select metrics and grains. The query
surface uses `mart_sales_daily`, `fact_forecast`, `metric_definitions`,
`pipeline_metadata`, `dim_store` and `dim_product`. Evaluation independently
checks aggregates and `forecast_evaluation`; it is not a user query tool.

## Metric semantics

`units` sums observed demand. `revenue_proxy` is unknown when any selected
price is missing; `known_revenue_proxy` reports only the priced subset and
stays unknown when no prices exist. `price_coverage` divides priced rows by
all selected rows. Missing prices are never filled with zeros.

Rolling metrics reuse Gold's past-only columns: sum series within a day, then
average valid daily sums over the selected interval. Missing rolling history
is counted and disclosed. Spike output counts canonical true flags and
includes a heuristic/noncausal warning. `data_freshness` is a global snapshot
measure relative to Gold's `as_of_date`, not the wall clock. It rejects date
or segment filters. Units comparisons use an immediately preceding interval
of equal length; percentages remain unknown when the prior value is zero.

Forecasts keep each model/split separate. WMAPE is
`sum(abs(actual_units-predicted_units))/sum(abs(actual_units))`; it never
averages percentages. MAE and RMSE use observation-level errors. A zero WMAPE
denominator is explicit. Source run IDs must match current Gold, historical
actuals must exist and future actuals must be absent. LightGBM future requests
are refused because no operational future LightGBM output exists. Future
baseline predictions extend from a historical origin, not from today's date.

No inventory, stockout, current-sales, audited-revenue or causal claim can
be inferred from this historical dataset. The assistant explains these limits.

## Approved references

The exact corpus is `docs/metric_catalog.md`, `docs/data_dictionary.md`,
`docs/model_card.md`, `docs/baselines.md` and `docs/agent_faq.md`.
Lexical retrieval returns at most five excerpts, each at most 1,200 characters,
from files no larger than 128 KiB. Paths must resolve inside the approved
documentation directory; file symlinks are excluded. Citations contain actual
document names, sections and line ranges. Obvious instruction-bearing or
oversized excerpts are excluded. Retrieved text is quoted data only and is
never sent to an execution tool or used as provider instructions. Injection
filtering is supplemental; quoting documents cannot execute them.

## Optional local provider

Ollama is accessed only through explicit numeric loopback HTTP addresses.
Proxy settings and redirects are disabled; requests have socket timeouts and
an elapsed-time check between response reads. Responses are bounded to 64 KiB
and generation to 600 tokens. Discovery uses a two-second socket timeout;
chat uses thirty seconds by default, also its maximum configured timeout.
This accommodates the measured cold load of the existing local model.
A final blocking socket operation may take
its timeout before the elapsed-time check runs.

The adapter uses [Ollama structured outputs](https://github.com/ollama/ollama/blob/main/docs/capabilities/structured-outputs.mdx)
with the closed `Plan` schema. Every proposal is revalidated and must equal
the deterministic scope exactly. Missing, malformed, unsupported or altered
proposals trigger an explicitly labeled fallback. No provider-generated
answer text is displayed. The model therefore confirms supported intent; it
does not expand the deterministic grammar or invent missing business scope.
The prompt makes the confirmation role explicit: preserve all candidate
arguments and copy documentation queries verbatim. The same full `Plan`
schema, argument validation and exact equality check still apply; a changed
scope is rejected rather than repaired or accepted. No model download, paid
API, credentials or external service is required. Unit tests mock the
protocol; real-model runs are recorded separately in the RP-09 gate.

Diagnostics distinguish connection refusal, other connectivity errors,
timeouts, HTTP status errors, invalid API JSON, incomplete/truncated model
generation, invalid generated JSON, schema validation and scope mismatch.
Only allowlisted categories, numeric timing/token metadata, validation error
counts and application-owned changed-field names are exposed. HTTP bodies,
headers, URLs, prompts, generated content and exception messages are not
included. `Answer` and local traces carry `provider_diagnostic`.

Inputs rejected by preflight report `deterministic:preflight` and no model
attempt, even when Ollama is configured. A successful model selection alone
reports `ollama:<model>`. Explicit `--provider ollama` returns a nonzero CLI
exit code on fallback. Its golden evaluation requires genuine validated
selections for routed cases and reports preflight refusals separately.
Fallback may preserve functional correctness, but cannot pass live validation.

## Answers, errors and traces

`Answer` carries status, provider, selected tool, typed result and grounding
status. Supported numerical output includes measurement unit, period, filters,
source table, Gold run ID, generation time, historical freshness and warnings.
Empty results ask for clarification; null metrics retain their explanation.
Rendering uses returned values only, with six decimal places for display
and full precision retained in `ask --json`.

Local JSONL traces live under ignored `artifacts/agent/`. They contain a
request UUID, UTC time, tool/intent, an empty validated-filters field,
duration, source/run ID, outcome, error category, provider diagnostics and
grounding status. They omit raw questions, doc search text, credentials and results.
RP-11 removed filter values from runtime traces; typed API results still carry
their validated scope. See [observability](observability.md).
Trace-write errors fail closed with `trace_unavailable`. Operators may rotate
these local files; automatic retention management is not implemented.
`traces/sample.json` is an illustrative redacted record, not real M5 output.

The core `Assistant.ask` returns typed objects without CLI or web dependencies.
The RP-10 API reuses it with application-owned paths and configuration.
Authentication and public deployment remain outside this local demo.
