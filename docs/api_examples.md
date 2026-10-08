# Local API examples

Start the demo from the repository root. The API binds to loopback only.
OpenAPI: <http://127.0.0.1:8000/docs>; schema: <http://127.0.0.1:8000/openapi.json>.
The API version is `rp10-v1`; the package version remains `0.1.0`.

```powershell
.\.venv\Scripts\python.exe -m retailpulse demo
```

In a second PowerShell terminal:

```powershell
$api = 'http://127.0.0.1:8000'
Invoke-RestMethod "$api/health"
Invoke-RestMethod "$api/metrics/summary?store=CA_1&start_date=2016-04-01&end_date=2016-04-30"
Invoke-RestMethod "$api/forecast?split=test&models=lightgbm_global_v1&models=rolling_mean"
Invoke-RestMethod "$api/forecast?split=validation&store=CA_1&department=FOODS_1&horizon=7"
$body = @{question='How many units did CA_1 sell during April 2016?'; provider='ollama'} | ConvertTo-Json
Invoke-RestMethod "$api/assistant/query" -Method Post -ContentType 'application/json' -Body $body
```

For explicit offline routing, set `provider='deterministic'` in the body. In portable
mode use synthetic identifiers from `/health`, such as `SYN_A`, and the period
`2020-01-01` through `2020-02-11`. The synthetic example question is
`Show units for SYN_A from 2020-01-01 to 2020-02-11`.

| Endpoint | Contract and behavior |
|---|---|
| `GET /health` | Dataset availability, demonstration mode, API/package version, model availability, lineage and supported dimensions/forecast windows. A missing dataset returns HTTP 200 with `status=degraded` and `dataset=null`; clients must inspect these fields. |
| `GET /metrics/summary` | Optional paired ISO dates, `store`, `department`, `item`. Defaults to the source's observed period. Returns canonical KPIs, daily sums for the last 90 days of the requested range, and store/department comparisons for the full range. |
| `GET /forecast` | Repeated `models`, `split`, paired target dates, `store`, `department`, `item`, `horizon`, `demand_level`, `segmentation`, `limit`. Defaults to historical test LightGBM and rolling mean. Approved RP-09 forecast contract applies. |
| `POST /assistant/query` | JSON with a 2–1000-character `question` and optional `provider` (`ollama`, `deterministic`, `auto`; default `ollama`). Returns the RP-09 typed answer, tool result, grounding, safe diagnostics, elapsed time and explicit `live_provider_succeeded`. No conversational memory. |

Summary and forecast responses include `dataset` and `cached`. The dataset
contains the mode, Gold run, generation timestamp, observed period, snapshot
as-of date and exact freshness days. Its version combines those fields with
the database modification timestamp, size and file identity. A 60-second cache
holds at most 32 entries, keyed by dataset version, endpoint and normalized
typed filters. Source changes invalidate prior generations; changes during a
request fail safely. Assistant answers are never cached.

Canonical `revenue_proxy` is null when any selected observation lacks a price.
`known_revenue_proxy` sums only priced observations; the UI labels this as partial
and displays the missing count. Price coverage is a ratio. WMAPE is a ratio;
MAE/RMSE are units. Forecast rows represent separate models, never additive
model totals. A zero WMAPE denominator remains undefined. Future LightGBM
forecasts are not available.

## Errors and bounds

Unknown fields, identifiers containing SQL syntax, invalid dates, duplicate
scalar query parameters and unsupported models/providers are rejected. Repeated
distinct `models` parameters are intentional. No endpoint accepts SQL, paths,
tool definitions, credentials or database selection. Errors have this shape:

```json
{"error":{"code":"invalid_request","message":"Use only approved fields, identifiers, providers and ordered date bounds.","request_id":"request-specific UUID"}}
```

HTTP statuses include 400 (invalid host/body), 403 (origin/refusal), 408 (body
deadline), 413 (body over 4096 bytes), 414 (query over 2048 bytes), 415 (wrong
content type), 422 (invalid arguments), 503 (unavailable/busy) and 504 (query
timeout). Unexpected failures return a sanitized 500 without exception text.
The streamed body has a five-second total deadline. At most four requests
enter analytical execution concurrently. Gold sessions retain RP-09's read-only,
external-access-disabled connection, five-second query budget and 256 MB memory
limit. Summary work also has a 12-second budget checked between tool calls;
an in-progress tool may use its remaining five seconds. Ollama retains its
30-second request bound. The UI client uses a 65-second timeout and does not
honor proxy environment variables or follow redirects.

The application is a local demo, without authentication or multi-user deployment
claims. HTTP hosts are restricted to loopback; foreign browser origins are
rejected. Business questions are sent only to the selected local Ollama service.
The Streamlit server calls the API; the browser does not receive database access.

An assistant refusal, clarification or disclosed fallback can still return HTTP
200. Inspect `result.status`, `result.provider`, `result.provider_diagnostic`
and `live_provider_succeeded`; HTTP success alone is not evidence of LLM use.
