# M13 — Observability, Request Correlation & Operational Readiness

Implementation and local acceptance guide • 2026-09-09

## Review status and scope

M13 adds local structured operational telemetry, validated HTTP correlation, a database readiness probe, and a safe runtime diagnostic command. It reuses structlog, the existing FastAPI middleware and exception handlers, and the existing message `request_id` column. There are no dependencies, tables, migrations, external telemetry services, model changes, or frontend changes.

Baseline: `7e98f3bca1c9648240b272d47191e3a8ca8b81c2` (merge PR #10, M12). The repository was initially clean on `feature/automated-evaluation`; origin was fetched, local main was fast-forwarded to the merged M12 commit, and `feature/observability-readiness` was created from that clean main. Python is 3.12.4.

Pre-change acceptance: **129 Python tests passed in 6.23s; Node 10 passed, 0 failed**. The baseline was run before source edits.

No files were staged, committed, pushed, merged, or deployed during M13. Fetch and the authorized local main fast-forward/branch creation were the only Git mutations. M0–M12 retrieval, ingestion, persistence, models, guardrails, prompt construction, grounding sanitizer, conversation context, API response bodies, widget and evaluation gates remain functionally unchanged.

## File inventory

| File | Change and purpose |
|---|---|
| `app/core/telemetry.py` | New allowlist, finite error classification, safe structured events and timed stage observer. |
| `app/core/readiness.py` | New bounded asynchronous PostgreSQL/pgvector probe shared by API and CLI. |
| `app/api/routes/ready.py` | New `/api/v1/ready` endpoint and replaceable probe dependency. |
| `scripts/check_runtime.py` | New safe configuration/database/capability CLI, with Windows selector loop support. |
| `tests/observability/test_observability.py` | New deterministic M13 coverage with fake services/engines and captured JSON events. |
| `docs/M13-observability-readiness.md` | This implementation guide and operator runbook. |
| `app/api/middleware/request_id.py` | Extend existing correlation middleware to pure ASGI, validate IDs, inject headers, time requests, emit safe completion/failure events and restore context. |
| `app/application.py` | Move correlation middleware outside CORS so preflight short circuits also carry IDs. |
| `app/api/exception_handlers.py` | Replace raw error/traceback logging with safe finite classification; retain authoritative response bodies and statuses. |
| `app/api/router.py` | Register the readiness router. |
| `app/api/routes/chat.py` | Pass request state ID into the existing service argument; identify conversation-not-found in operational state. |
| `app/services/asta_service.py` | Observe guardrail bypass versus RAG and safe answer outcomes. |
| `app/rag/rag_service.py` | Time existing retrieval and LLM calls without altering arguments, results or branching. |
| `app/services/conversation_service.py` | Emit existing contextualized/grounded/model-used/source-count values after message persistence operations. |

The changes in frozen service files are additive observation hooks only. The explicitly reproduced corrections are described below. No frozen business algorithm was corrected or replaced.

## Request IDs

Every HTTP request reaching the application receives an ID. A single inbound `X-Request-ID` is accepted only when it matches ASCII `[A-Za-z0-9][A-Za-z0-9._-]{0,63}`: 1–64 characters, initial alphanumeric, subsequent alphanumeric, period, underscore or hyphen. Accepted IDs are preserved exactly, including case. Whitespace is not trimmed into validity. Missing, empty, invalid, overlong, or duplicated headers are replaced with a fresh UUID v4; rejected values are never logged or reflected by this middleware.

IDs are opaque correlation labels, not identities, authorization proofs or guaranteed unique values when supplied by a caller. Callers must not put personal data or secrets in an ID. Syntax validation cannot determine whether an otherwise valid opaque identifier was chosen from sensitive information.

The single ID is placed in `request.state.request_id` and structlog context variables, included in `X-Request-ID` on responses, and passed through the chat API to `ConversationService.send_message(request_id=...)`. The existing repository writes it to the existing user and assistant message `request_id` field. No duplicate ID system or persistence layer is added. No conversation ID is logged.

Context is restored with context-variable tokens after each request; concurrent requests are tested for isolation. Direct non-HTTP callers retain their existing optional request-ID behavior and do not require an invented HTTP ID.

The header covers successful requests, validation errors, conversation 404, handled application errors, ordinary unhandled 500, unknown routes, and CORS short circuits. The middleware uses the existing central unhandled-error handler before headers start, preserving the 500 body while preventing the ASGI server from printing the original exception for these failures. If a streaming response has already started, its header is already present; a later failure cannot replace its status/body and is re-raised after a safe failure event. Current chat responses are ordinary JSON, not streaming. Errors before the app receives an HTTP request cannot receive an application ID.

## Structured operational events

M13 uses the configured structlog JSON renderer and context variables in `app/core/logging.py`. No second logging framework or dependency is introduced. Operational events are emitted at INFO and therefore require INFO or a more verbose configured level. Existing timestamp and level processors remain in use.

All events include `event`, `service: Asta`, `version: 0.1.0`, safe `environment`, timestamp and level. Request-bound events include `request_id`. Environment accepts development, test, testing, staging, production or local; other configured labels become `other`. The telemetry helper temporarily excludes arbitrary ambient context so another caller's payload fields cannot be merged into M13 events.

| Event | Fields and meaning |
|---|---|
| `request_started` | `request_id`, finite HTTP `method`; emitted before routing, so no resolved route/status yet. |
| `request_completed` | `request_id`, method, route template, status_code, elapsed_ms, error_code. Elapsed time ends when ASGI processing returns, including response transmission work. |
| `request_failed` | Same completion fields for status >=400; also emitted for an exception after response start. |
| `application_error` | Safe finite error_code and request_id from the central handlers. |
| `stage_started` | stage: retrieval, llm or rag. |
| `stage_completed` | stage and elapsed_ms. |
| `stage_failed` | stage, elapsed_ms and finite error_code; exception is re-raised to the existing caller. |
| `chat_outcome` | path, outcome, grounded, model_used, source_count. |
| `conversation_outcome` | contextualized, grounded, model_used, source_count and available request_id. |

Elapsed values are finite nonnegative milliseconds measured with a monotonic performance counter. Nested stage times overlap and must not be summed. A conversation outcome occurs before the API's transaction commit; the request completion event is the final HTTP outcome if commit subsequently fails.

Safe route templates are `/api/v1/health`, `/api/v1/ready`, `/api/v1/chat/conversations`, and `/api/v1/chat/conversations/{conversation_id}/messages`. Unmatched or unrecognized routes are labelled `unmatched`. This deliberately bounded list prevents raw URL/path data entering telemetry. With a nondefault API prefix, route labels currently fall back to unmatched; request correlation still works.

An illustrative completion event (timestamp omitted here):

```json
{"event":"request_completed","service":"Asta","version":"0.1.0","environment":"development","request_id":"m13-missing","method":"POST","route":"/api/v1/chat/conversations/{conversation_id}/messages","status_code":404,"elapsed_ms":12.4,"error_code":"conversation_not_found"}
```

### Explicit do-not-log list

The helper accepts known safe field names and validates their value types or finite values. It drops arbitrary extras. M13 telemetry never accepts request bodies, user messages/questions, answers, system/user prompts, hidden instructions, retrieved chunks or source content, source titles/filenames, authorization headers, cookies, API keys, passwords, DB URLs, raw settings, query strings, raw exception messages, exception class names or tracebacks. Model names are deliberately omitted; `model_used` is a boolean. Source count is an integer; source identities are omitted.

This is an allowlist for M13 operational events, not a universal sanitizer of every third-party logger. Run the server with access logging disabled as shown below: default server access logs may include raw URLs and query strings. Do not enable provider or HTTP debug logging when investigating production incidents. Existing liveness/startup conventions remain unchanged.

## Chat execution semantics

- `path=guardrail_bypass`, `outcome=bypass`: existing guardrails supplied a deterministic response, including greetings/off-topic/injection refusals. There is no RAG/retrieval/LLM invocation. `grounded=false`, `model_used=false`, `source_count=0` are expected, not an error.
- `path=rag`, `outcome=insufficient_information`: RAG ran, retrieval returned no evidence, and the existing deterministic insufficient-information answer bypassed the LLM. `model_used=false`, `source_count=0`.
- `path=rag`, `outcome=grounded`: the existing RAG service retrieved evidence, invoked the LLM and applied its existing sanitizer. The grounded flag is the existing service result, not a new independent quality assertion. `model_used=true` under the current live pipeline.
- `contextualized` comes directly from the existing conversation context builder. It does not disclose the contextualized question or history.

A failed retrieval/provider call generates stage_failed and the request's final finite error code, rather than a successful chat outcome. Retrieval and RAG wrappers observe existing boundaries without retries, model swaps, new thresholds or output mutations.

## Finite error codes

| Code | Interpretation/action |
|---|---|
| `none` | Successful HTTP completion. |
| `validation_error` | HTTP 422; inspect caller input locally without adding it to logs. |
| `conversation_not_found` | Existing ConversationNotFoundError/404; widget should use its existing explicit new-chat flow. |
| `database_unavailable` | SQLAlchemy failure or failed readiness capability; check the local DB service/config/extension. This intentionally coarse label is not proof of a particular database root cause. |
| `provider_unavailable` | Existing LLMRequestError or empty provider response; correlate ID and retry through existing user flow when appropriate. Readiness may remain 200. |
| `configuration_error` | Existing app/LLM configuration error, or CLI config failure. Verify configuration privately. |
| `application_error` | Other existing AstaError. Public API response remains unchanged. |
| `http_error` | Other HTTP >=400, including ordinary unknown routes/CORS rejection. |
| `internal_error` | Other exceptions or unclassified server errors. Correlate stages and reproduce locally. |

Operational classification is separate from public error codes. Existing AstaError still returns its existing 400 contract, including the existing public message; this milestone does not broaden its body. Existing validation and conversation 404 bodies remain unchanged. An ordinary unhandled exception still returns 500:

```json
{"error":{"code":"INTERNAL_SERVER_ERROR","message":"An unexpected error occurred."},"request_id":"m13-example"}
```

## Liveness versus readiness

`GET /api/v1/health` is the unchanged M2 liveness endpoint. It indicates that the HTTP process responds; it does not query PostgreSQL or any provider. Example 200:

```json
{"status":"healthy","service":"Asta","version":"0.1.0","environment":"development"}
```

`GET /api/v1/ready` performs a bounded DB connection and `SELECT 1`, then checks for the `vector` extension in `pg_extension`. It reuses the configured engine and connection pool, including the existing vector registration hook. Connections are released using asynchronous context managers. The probe has a five-second asyncio timeout covering acquisition and queries. Driver cancellation/cleanup and a blocked event loop can add scheduling delay; this is not an external watchdog.

Example 200:

```json
{"status":"ready","service":"Asta","version":"0.1.0","components":{"database":"ready","pgvector":"ready"}}
```

Example 503 when connection fails:

```json
{"status":"not_ready","service":"Asta","version":"0.1.0","components":{"database":"unavailable","pgvector":"unavailable"}}
```

If the first query succeeds but vector capability is absent or the second query fails, database can be `ready` while pgvector is `unavailable`; status is still 503. The existing vector connection-registration hook can reject a missing extension before the first query, causing both components to be unavailable. Bodies never disclose hostnames, SQL, credentials or exception text. Environment is omitted from the new readiness body to keep it minimal.

Readiness never invokes Groq, downloads/loads HF weights, or warms embedding/reranker models. It does not prove corpus completeness, schema compatibility beyond the checked capability, model-cache availability, provider reachability or answer quality. Groq incidents should not make the process appear dead or force DB readiness to fail. Missing app/provider configuration can fail the separate runtime CLI while DB-only readiness remains healthy.

## Runtime diagnostic CLI

From the repository root in PowerShell:

```powershell
Set-Location D:\Projects\Asta-WebPortal-AI
.\.venv\Scripts\python.exe -m scripts.check_runtime
$LASTEXITCODE
```

Expected success:

```text
config: PASS
database: PASS
pgvector: PASS
0
```

Configuration checks load the existing Settings validation, require a PostgreSQL+Psycopg URL with a database name, nonblank Groq key/model and embedding/reranker model configuration. Values are not printed. These are presence/shape checks, not credential validation. Failure to validate config stops before connecting:

```text
config: FAIL (configuration_error)
```

Database failure after config passes:

```text
config: PASS
database: FAIL (database_unavailable)
pgvector: FAIL (database_unavailable)
```

Exit 0 means mandatory checks passed; exit 1 means config, readiness or runtime failure. Invalid CLI arguments use argparse's standard exit 2. `--help` describes the command. No optional Groq probe or cache check is implemented; there are no downloads, model loads or provider calls. The CLI disposes its engine and uses the Windows selector event loop required by async Psycopg. Deterministic tests exercise success and deliberate failure; no local DB was deliberately disabled.

## Local operator workflow

Start the existing FastAPI app with safe access-log settings. The following exact Windows command also selects the Psycopg-compatible event loop:

```powershell
Set-Location D:\Projects\Asta-WebPortal-AI
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
.\.venv\Scripts\python.exe -c "import asyncio, uvicorn; asyncio.run(uvicorn.Server(uvicorn.Config('app.main:app', host='127.0.0.1', port=8013, access_log=False)).serve(), loop_factory=asyncio.SelectorEventLoop)"
```

In a second terminal:

```powershell
curl.exe -i http://127.0.0.1:8013/api/v1/health
curl.exe -i http://127.0.0.1:8013/api/v1/ready
curl.exe -i -H "X-Request-ID: operator-check-001" http://127.0.0.1:8013/api/v1/health
curl.exe -i -H "X-Request-ID: invalid value" http://127.0.0.1:8013/api/v1/health
```

Expect 200 for both probes when DB-ready, exact echo of operator-check-001, and a generated UUID for the invalid ID. All responses include X-Request-ID.

For a widget/API incident, inspect the failed HTTP call in browser developer tools and copy only its response X-Request-ID, status and approximate time. Search captured JSON lines by exact request_id. Inspect request_completed/request_failed, followed by stage and outcome events for that ID. Do not share a HAR, request body, conversation transcript, bearer token, cookie or screenshot containing them. An operator can provide a fresh opaque ID on a direct API reproduction if needed.

M11 remains frozen and does not add a new ID display. CORS remains at its existing policy; M13 does not expose the header to cross-origin JavaScript or enable staging origins. Developer tools/direct clients can inspect it. Future staging integration must make its own reviewed CORS/header-exposure and authentication decisions.

## Test and acceptance evidence

Baseline commands (before implementation):

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp=.cache/m13-baseline-tmp
node --test frontend/tests/chat-client.test.mjs
```

Baseline: Python 129/129; Node 10/10.

M13 adds 37 deterministic test cases, including:

- Generated/replaced/preserved IDs, boundary length, duplicate values, handled and unhandled errors, CORS short circuit and concurrent context isolation.
- Required request completion fields and finite nonnegative elapsed time; unknown raw paths/query/header content absent from JSON telemetry.
- Denial of payload/answer/prompt/credentials/DB URLs and arbitrary ambient context; provider failure with synthetic secret is classified without leakage.
- Real API-to-service-to-fake-repository propagation for both existing message records; unchanged chat response fields and validation/404 contracts.
- Guardrail bypass, no-evidence bypass and grounded RAG using fakes; stage invocation and model-used semantics.
- Readiness success, missing vector, connection failure and timeout; exact lightweight queries; model loaders and Groq generate patched to fail if called.
- Finite exception categories; runtime CLI config/success/failure exit paths without a live provider or intentionally broken DB.

Final commands:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp=.cache/m13-final-review-tmp
node --test frontend/tests/chat-client.test.mjs
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
.\.venv\Scripts\python.exe -m scripts.run_evaluation --report data/evaluation/results/m13-final-local.json
$LASTEXITCODE
```

Final acceptance: **166 Python tests passed, 0 failures, 0 errors, 0 skipped; Node 10/10 passed. M12 live evaluator 17/17 PASS, overall PASS, exit 0.** Final run ID: `102357d0-f1f8-4607-a304-f68edaa72b1f`. Its mandatory regression subprocesses verified the final test set. The companion acceptance summary contains safe structured evidence without evaluation answer content.

Final live acceptance results: retrieval 5/5, supported_answer 5/5, unsupported 2/2, guardrail 4/4, conversation 1/1; overall PASS, exit 0. M12 gates and golden cases are unchanged. The generated evaluator JSON remains ignored under data/evaluation/results and must not be staged. Reports can contain evaluation answer content and are not operational logs; the attached acceptance summary deliberately omits it.

Live localhost TCP checks passed with real DB, cached models and live Groq:

| Check | Observed |
|---|---|
| Liveness | 200, original body, generated UUID header. |
| Readiness | 200, database/pgvector ready, generated UUID header. |
| Valid ID echo | 200, m13-manual-echo preserved. |
| Greeting | 200, 0 sources, guardrail_bypass/bypass correlated to m13-greeting. |
| Grounded APN | 200, 1 source, rag/grounded correlated to m13-grounded_apn. |
| Off-topic | 200, 0 sources, guardrail_bypass/bypass correlated to m13-off_topic. |
| Fake conversation | 404, original safe detail body, m13-missing header and classification. |
| Captured server log privacy | PASS: tested messages, returned answers, full system prompt, configured key/DB URL and synthetic Authorization/Cookie values absent. |

Manual checks created three local conversations through the existing API. They were not deleted. The M12 evaluator retains its existing rollback behavior. Temporary server logs/test helpers are outside repository deliverables. No live DB outage was induced. Ruff is not installed in the existing virtual environment, so no Ruff lint result is claimed; no dependency was installed for it.

## Reproduced frozen integration corrections

Before edits, a temporary in-memory test route raised RuntimeError with a synthetic secret marker:

1. A health request carrying `X-Request-ID: unsafe value` echoed that invalid value unchanged.
2. The synthetic unhandled 500 returned no X-Request-ID header.
3. The existing central logger emitted a traceback containing the synthetic secret. The application-error handler also directly logged its message.

Corrections are restricted to correlation/exception telemetry: conservative ID validation, outer placement relative to CORS, ASGI header injection, existing central 500 response reuse, and finite error events in central handlers. Tests reproduce and protect all three cases. No real credential was used in this reproduction. No retrieval/model/guardrail/conversation-context defect was found or corrected. Frozen service edits only observe existing execution boundaries and metadata.

## Limitations and deferred work

Logs are local, process-scoped JSON output: no durable log service, metrics backend, dashboards, tracing vendor, alerting, retention policy or cross-process aggregation. IDs can correlate externally collected logs, but this milestone does not deploy a collector. Logs require INFO visibility and a working output sink. The allowlist cannot protect unrelated third-party/server logging; the documented launch disables raw access logs. A failure after a streaming response starts can still reach server error logging; current chat is nonstreaming.

No staging WebPortal integration, auth redesign, Docker/Kubernetes, CI/CD, database migration, model swap, external telemetry vendor or Sentry expansion. Readiness is intentionally DB capability readiness, not complete end-to-end availability. No schema/corpus/cache/model/provider warmup is attempted. No application secrets or content are added to operational storage; existing messages continue using their existing persistence contract.

## Git review and future commands — not executed

Review the 14 files in the inventory; eight tracked source files are modified and six files are newly created. All changes are unstaged. No migration, dependency, frontend, prompt, model config or M12 golden/gate file is changed. Use:

```powershell
git status --short
git diff --check
git diff --stat
git diff
```

Untracked new files are not included in ordinary git diff; open them separately during architecture review. Git's LF/CRLF advisory on Windows is not a test error.

Only after architecture approval, the user may execute these exact future commands (Codex did not execute them):

```powershell
git add app/api/exception_handlers.py app/api/middleware/request_id.py app/api/router.py app/api/routes/chat.py app/api/routes/ready.py app/application.py app/core/readiness.py app/core/telemetry.py app/rag/rag_service.py app/services/asta_service.py app/services/conversation_service.py scripts/check_runtime.py tests/observability/test_observability.py docs/M13-observability-readiness.md
git diff --cached --check
git diff --cached --stat
git commit -m "feat: add safe observability and runtime readiness"
git push -u origin feature/observability-readiness
```

Do not stage generated evaluator results, local transcripts, logs, .env or test temp directories. M13 local acceptance passed and is ready for architecture review; no deployment or merge is part of this delivery.
