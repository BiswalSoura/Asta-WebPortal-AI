# M14 — WebPortal Integration Bridge & Staging Contract

Status: implemented for architecture review. Automated acceptance and local navigation/session flows pass. Actual browser 200% zoom remains a manual acceptance item; real WebPortal staging requires the team information listed below. This is not production authentication or deployment approval.

## Baseline and scope

Repository: `D:\Projects\Asta-WebPortal-AI`.

Fetched `origin` and fast-forwarded local `main` to the merged M13 commit `3f7b0512ee2cb929324bd16fc6b55454eb7cc280` (Merge pull request #11). The working tree was clean before changes. Created `feature/webportal-integration-bridge` from that commit. HEAD remains that baseline; nothing was staged, committed, pushed, merged, or deployed by this task. Updating local main was the requested fast-forward refresh, with no new merge commit.

Actual runtime: Python **3.12.4**, Node **v24.19.0**. Before source changes: **166 Python passed**, **10 Node passed**, zero failures/errors/skips. The PostgreSQL/pgvector, model, retrieval, prompts, sanitizer, guardrails, conversation algorithms, dependencies and migrations were not changed.

## Files and purpose

| File | Change and purpose |
| --- | --- |
| `app/core/config.py` | Modified: exact-origin CORS settings and validation, request-ID exposure switch |
| `app/application.py` | Modified: pass reviewed origins/exposure settings to existing CORS middleware |
| `app/schemas/chat.py` | Modified: optional strict conversation-creation metadata schema |
| `app/api/routes/chat.py` | Modified: pass validated page identifier into existing service/JSONB column |
| `frontend/js/asta-client.mjs` | Modified: opt-in UUID storage, safe restore/reset, pending-response invalidation, page-context/API-base validation |
| `frontend/js/asta-widget.js` | Modified: retain original M11 auto-mount entry, delegating to shared UI |
| `frontend/js/asta-widget-core.mjs` | Created by moving/reusing M11 UI: mount API, safe label, reset hook and back/forward-cache reconciliation |
| `frontend/js/asta-embed.mjs` | Created: public host initialization module; one instance per document |
| `frontend/host.html` | Created: generic M14 host simulation with two contexts |
| `frontend/css/host.css` | Created: simulation host styling only |
| `frontend/js/host-demo.mjs` | Created: full navigation/SPA context demo, logout, UUID-only storage diagnostics, unknown-conversation test button |
| `frontend/tests/embed.test.mjs` | Created: 12 deterministic M14 Node tests |
| `scripts/local_web.py` | Modified: explicit JavaScript MIME serving for allowlisted shared modules on Windows |
| `scripts/local_host.py` | Created: local-only M14 fixture launcher using existing app factory and safe logging |
| `tests/integration/test_webportal_bridge.py` | Created: 12 Python cases for metadata, CORS and fixture serving |
| `docs/M14-webportal-integration-bridge.md` | Created: this implementation/handoff/acceptance contract |

The M11 HTML, CSS, original 10 client tests, M12 evaluator/golden cases, M13 telemetry implementation and observability tests remain unchanged. This is one widget, with its UI extracted into a reusable module, not a replacement widget.

## Host inclusion and initialization

Publish the existing `frontend/js` and `frontend/css` asset trees together, preserving relative paths. Only public assets belong in the host static directory; never serve the repository root. Serve `.mjs` with a JavaScript MIME type. No framework, npm package, bundler, global namespace or inline script is required.

In the shared host layout:

```html
<div id="asta-container"></div>
<script type="module" src="/assets/host-asta-init.mjs"></script>
```

In the host-owned external module `/assets/host-asta-init.mjs`:

```js
import { initAsta } from '/assets/asta/js/asta-embed.mjs';

const asta = initAsta({
  container: document.getElementById('asta-container'),
  apiBase: '/api/v1/chat',
  launcherLabel: 'Ask Asta',
  pageContext: 'approved-page-id',
});

// Call from the actual host navigation callback after confirming its contract.
asta.setPageContext('another-approved-page-id');

// Call from the actual logout/account-switch callback, before leaving the page.
// No particular WebPortal event name or authentication mechanism is assumed.
function resetAssistantForHostSessionChange() {
  asta.resetSession();
}
```

The sample identifiers are generic contract examples, not real WebPortal routes.

| Configuration | Contract |
| --- | --- |
| `container` | Existing DOM element; defaults to `document.body`. Initialize after it exists. A dedicated child with `data-asta-embed` receives the Shadow DOM. |
| `apiBase` | Chat API prefix, default `/api/v1/chat`; root-relative path or absolute HTTP(S) URL, trailing slashes normalized. No protocol-relative URLs, credentials, whitespace, query, fragment, percent-encoded paths, backslashes or dot segments. Use HTTPS for a real HTTPS host. |
| `launcherLabel` | Nonempty string up to 80 characters; rendered with `textContent`. |
| `pageContext` | Optional validated non-sensitive identifier, default `null`. |

Unknown configuration fields throw, including attempted identity/role/permission fields. Initialization is idempotent for the same container: returns the existing API, with first initialization configuration retained. Use `setPageContext()` for subsequent context changes. A second container in the same document is rejected to prevent competing clients sharing the UUID key. Keep the container in the stable master layout for SPA navigation; do not remove/recreate it on every route.

Returned API: `open()`, `close()`, `setPageContext(value)`, `getPageContext()`, `getConversationId()`, `resetSession()`. Getters expose only correlation/context information, not authorization. The widget remains fixed at the existing bottom-right placement; no new placement system is introduced. Choose a host container without transforms, clipping or stacking contexts that interfere with fixed positioning, and review overlays with the host team.

The existing Shadow DOM template, CSS, plain-text answers/sources, error messages, Enter/Shift+Enter/IME handling and Escape-to-close behavior are reused. The original `/m11/` entry still uses memory-only conversation state and starts fresh on refresh.

## Conversation continuity and browser storage

Exactly one integration key is written:

```text
aa.asta.m14.conversation-id
```

Its value is only the opaque 36-character UUID. Storage is `sessionStorage` on the **host page origin**, scoped to the tab. It survives normal full reload/navigation on that origin. Use one Asta API environment per host origin/tab; reset before switching API environments. Cross-origin host navigation does not share storage. Browser duplicate-tab/session-recovery behavior is browser-controlled and is not a user identity guarantee.

No messages, transcripts, answers, prompts, sources, drafts, page context, user identifiers, roles, permissions, authentication tokens, API keys or secrets are written to browser storage. The implementation does not write `localStorage`. Context and the visible transcript exist only in memory. Reload restores the UUID, not earlier transcript bubbles; the backend's existing conversation history supplies follow-up context. No new history-reading API is introduced.

Invalid/corrupt UUIDs are ignored and removed. Unavailable storage falls back to page-memory behavior; continuity cannot be promised when the browser denies storage. The host must not depend on browser storage as an authentication or security boundary.

New chat clears the UUID and visible transcript; the next explicit send creates a new server conversation. Existing M11 recovery behavior preserves an uncertain question in the composer after New chat, requiring the user to send it explicitly. Ordinary New chat clears the draft.

404 clears the stored UUID and requires explicit New chat. Network failures, malformed replies, timeouts and other uncertain message POSTs also remove the persisted UUID and require explicit reset in the current document. No uncertain POST is automatically replayed, including after navigation. 422/429 retain the existing explicit retry behavior.

`resetSession()` clears UUID, draft, transcript, errors, pending UI status and page context, then closes the widget. Late responses cannot repopulate state or issue a subsequent message after reset during conversation creation. Server-side requests already submitted may still finish; reset does not delete server records or guarantee server cancellation. The host should withhold further chat access as appropriate during logout; M14 does not implement that authentication decision.

Back/forward-cache restoration reconciles the UUID from current session storage and discards cached transcript/draft state so an old document does not revive a session cleared on another page. Deterministic test coverage verifies this path.

## API and page-context trust boundary

Endpoints consumed:

```text
POST {apiBase}/conversations
POST {apiBase}/conversations/{conversation_uuid}/messages
```

Creation still accepts no body. Optional body:

```json
{"page_context":"approved-page-id"}
```

`page_context` is null or 1–128 ASCII characters: starts with an alphanumeric character, followed only by alphanumerics, dot, underscore, colon or hyphen. Empty strings, HTML, URLs, objects and overlong values are rejected. Creation rejects unknown fields. The old response remains `{conversation_id, status}` and message requests remain `{message}` with the unchanged M10 response schema.

The existing `Conversation.page_context` JSONB column safely stores:

```json
{"host_page_context":"approved-page-id"}
```

This is a **creation-time snapshot**. Updating page context during SPA navigation or restoring an existing conversation changes current client metadata only; it does not update that stored snapshot. Future conversations use the latest value. No per-message context field or update endpoint was invented.

Inspection found the existing service already passes this column to the repository and does not use it for retrieval, prompt building, guardrails or permissions. No migration/service/model/repository change was needed. A live database read after the browser test confirmed `host_page_context=fixture-a`, `user_role=null`, `permission_context=null` even after navigation to B.

This identifier is untrusted, non-authoritative metadata. It grants no permissions, proves no identity, and does not change answers or access decisions. Do not put personal data or secrets into it. Syntax validation cannot determine whether a host-selected identifier is sensitive. Trusted server-side user/session binding remains deferred.

## Same-origin, cross-origin, CORS and request IDs

Same-origin: use `/api/v1/chat` or the confirmed host reverse-proxy prefix. No CORS allowance is necessary.

Separate API origin example:

```js
const asta = initAsta({ apiBase: 'https://asta-api.example.test/api/v1/chat' });
```

The domains here are examples requiring replacement by confirmed team values. In API environment configuration, following existing Settings conventions:

```dotenv
ASTA_CORS_ALLOWED_ORIGINS=["https://portal.example.test"]
ASTA_CORS_EXPOSE_REQUEST_ID=true
```

Defaults remain `[]` and `false`: no cross-origin access and no automatic header exposure. Origin entries must be exact HTTP(S) origins without a path/trailing slash, credentials, query, fragment or wildcard. Port is part of the origin. Use a JSON array, not comma-separated text. Restart the API after changing settings.

Existing `allow_credentials=True` is preserved, but the widget deliberately continues `credentials: 'omit'` for every request and has no credential/token configuration. CORS is not authentication. Do not turn credential omission into credential inclusion until the authentication/CSRF/session contract has been reviewed in a later milestone.

M13 still creates/validates `X-Request-ID` and returns it on HTTP responses, including errors and preflight. The widget does not persist request IDs or expose raw response bodies. Support staff can inspect request IDs in the browser Network panel. Enabling the reviewed exposure setting allows browser JavaScript to read the header on CORS-managed responses; it does not add a new widget diagnostics API. Existing outer error handling is preserved, so an unhandled 500 may still be blocked by browser CORS rather than made readable; do not infer that exposure alone guarantees browser readability of every failure.

No content/body/page-context/identity fields were added to M13 telemetry. Local launcher disables Uvicorn access logs. Normal structured request and outcome events were observed without question/answer bodies or secrets. Existing finite route/error classifications remain unchanged.

CSP must allow module imports from the asset origin, the Shadow DOM stylesheet under `style-src`, and the API under `connect-src`. Use a host-owned external initialization module or the team's approved nonce policy; no `unsafe-inline` requirement is introduced by the integration. A Trusted Types enforcement policy or unusual host CSP must be tested with the WebPortal team because the reused fixed M11 template uses `innerHTML`; dynamic user/host text does not.

## Local fixture and acceptance

From repository root:

```powershell
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
.\.venv\Scripts\python.exe -m scripts.local_host
```

Open `http://127.0.0.1:8014/m14/`. This serves the fixture and existing API on loopback; it is not a staging deployment. `/m11/` remains available. The normal `app.main:app` does not gain fixture/static routes. Stop with Ctrl+C in the launcher terminal.

The fixture offers reload links for `fixture-a`/`fixture-b`, a no-reload context switch, logout/account reset, UUID-only diagnostics and an explicit unknown-conversation test button. These are simulation controls, not a production host API. No proprietary WebPortal markup or actual routes were copied.

Observed local browser acceptance on 2026-09-09:

| Check | Result |
| --- | --- |
| Grounded APN question in context A | PASS; grounded answer with sources |
| Full navigation to context B | PASS; UUID `0390aacb-f09e-40ad-86f8-8811f1243345` reused, prior bubbles not restored |
| Follow-up “Can you explain that option?” | PASS; answer explained APN/Parcel Number using retained server context |
| No-reload context switch | PASS; context changed to A, same widget/visible conversation retained |
| New chat | PASS; next send created a different UUID (`cce27615-2a34-4e96-a863-2e5cca4e47e5`) |
| Logout/account reset then reload | PASS; UUID absent, UI reset; session/local storage counts both zero |
| Greeting | PASS; normal Asta greeting |
| “Tell me a joke.” | PASS; WebPortal scope response |
| Prompt-injection request | PASS; internal-instruction refusal, no internal content |
| Fake UUID 404 | PASS; explicit recovery message, draft retained, Send disabled, UUID removed, zero storage keys |
| Explicit New chat after 404 | PASS; next explicit send created a fresh UUID, greeting succeeded |
| Storage after successful conversation | PASS; exactly one session key with a valid UUID, local storage zero; deterministic tests verify exact key/value and no content |
| Readiness/request ID | PASS; HTTP 200, database/pgvector ready, `X-Request-ID` present |
| Desktop and 390×844 mobile | PASS; inspected panel, composer, error/recovery and controls |
| Enter and Escape | PASS; Enter submitted once, Escape closed and focused launcher |
| Reduced viewport 640×360 | Checked; controls and scrollable message area remained usable |
| Actual 200% browser zoom | **NOT VERIFIED**: in-app browser zoom shortcuts had no visible effect and no zoom control was exposed. Repeat in the target browser before freezing M14. Reduced viewport is not claimed as equivalent acceptance. |

Manual test conversations remain ordinary local server records; reset intentionally does not delete them. Cross-origin behavior was tested deterministically through ASGI preflight/response tests, not against a real WebPortal staging origin.

## Automated validation and evidence

Baseline commands (before edits):

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp=.cache/m14-baseline-tmp
node --test frontend/tests/chat-client.test.mjs
```

Results: **166 Python / 10 Node passed**.

Final commands:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp=.cache/m14-final-verified-tmp
node --test frontend/tests/*.test.mjs
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
.\.venv\Scripts\python.exe -m scripts.run_evaluation --report data/evaluation/results/m14-live.json
$LASTEXITCODE
```

Results: **178 Python passed**, **22 Node passed (existing 10 + new 12)**, zero failures/errors/skips. New Node coverage includes storage/no-content writes, corrupt/denied storage, safe 404/uncertain POST recovery, reset races, API validation, host mount/idempotency, safe text rendering, context updates, UI reset, and cached-page restoration. Python coverage includes exact origin allow/deny, preflight, request-ID exposure, strict metadata/identity rejection and asset MIME/private-path checks. Existing M11 and M13 tests remain green.

Live M12 report: `data/evaluation/results/m14-live.json`; run ID `2f5b0d60-45b7-43d1-b6ec-b53452482988`.

| Category | Result |
| --- | --- |
| retrieval | 5/5 PASS |
| supported_answer | 5/5 PASS |
| unsupported | 2/2 PASS |
| guardrail | 4/4 PASS |
| conversation | 1/1 PASS |

**17/17 PASS, overall PASS, exit 0. Top-1=1.000, Recall@K=1.000, MRR=1.000.** The frozen evaluator still runs its original 10-test Node gate; the full 22-test Node command was run separately. The live evaluation preceded the final frontend-only cached-page/test refinements; backend and evaluation behavior were unchanged afterward. Full Python and Node checks were rerun after those refinements. Reports remain in the existing ignored results directory.

Security evidence: creation forwards only the validated metadata wrapper; identity/permissions are rejected. Real stored role/permissions remained null. Browser content is rendered as text; a hostile-answer test creates no child HTML elements. Storage tests assert exactly the namespaced UUID entry. Pending creation and pending-answer reset tests prevent stale UI/storage restoration. No new telemetry field, retry loop, credential persistence, migration or dependency was added.

## Information required from the WebPortal developer

Before real staging integration, obtain all of the following:

1. Shared/master layout insertion point, asset ownership and stable container location; stacking/overlay constraints.
2. Frontend and server technologies, supported browser versions, and static module/MIME support.
3. Actual authentication/session mechanism, session lifetime and account-switch semantics; do not assume JWT, cookie type, SSO provider or role mapping.
4. Same-origin reverse proxy versus separate API origin, exact API prefix and asset origins.
5. CSP directives, nonce strategy, Trusted Types enforcement and approved `connect-src`/`style-src`/`script-src` values.
6. Exact staging origins/ports for CORS and whether request-ID header exposure is approved.
7. The actual logout/account-switch hook and ordering, including forced expiry and navigation away; who calls `resetSession()`.
8. Navigation model: full reload, SPA, partial replacement, browser back/forward cache, and where context updates are delivered.
9. Approved non-sensitive page identifiers and ownership of their mapping; no guessed real route names.
10. How and where a trusted **server-side** user/session identifier can later reach Asta, including verification boundary, issuer/session authority, lifecycle and revocation. Browser configuration must not become the trusted bridge.

Implemented now: host module, one reused widget, UUID-only same-tab continuity, validated non-authoritative creation metadata, reset hook, configurable exact CORS/header exposure, local fixture and regression coverage.

Requires confirmation/later work: real layout placement, CSP integration, trusted identity/user binding, permissions, credentials/CSRF/session transport, enforced logout/expiry, real staging origins and deployment. No production-auth claim is made by a conversation UUID or a successful local integration test.

## Corrections, limitations and Git review

No reproduced frozen retrieval/model/guardrail/conversation algorithm defect was corrected. Changes to completed files are the narrow M14 integration additions listed above. Within M14, browser testing caught fixture encoding and shared-module MIME needs; these were fixed locally. Pending-reset and cached-page races have regression tests. The M11 stylesheet and keyboard behavior were retained.

Known limits: no transcript restore endpoint; one integration instance and one API environment per host origin/tab; fixed existing placement; storage may be denied; no server deletion/cancellation; page metadata snapshot is not updated on existing conversations; actual 200% zoom remains pending; real host authentication/CSP/cross-origin staging requires team confirmation. No Docker, Kubernetes, CI/CD, model, migration or deployment expansion was performed.

`git diff --check` passed (Git may emit its existing Windows LF/CRLF advisory). Final scope is seven modified tracked files and nine new files, including this document, as listed above. No staged changes. Generated evaluation reports are ignored. HEAD is still the baseline commit on `feature/webportal-integration-bridge`.

Future commands **for the user after architecture review and remaining acceptance**, not executed:

```powershell
git status --short
git diff --check
git add app/core/config.py app/application.py app/schemas/chat.py app/api/routes/chat.py frontend/js/asta-client.mjs frontend/js/asta-widget.js frontend/js/asta-widget-core.mjs frontend/js/asta-embed.mjs frontend/host.html frontend/css/host.css frontend/js/host-demo.mjs frontend/tests/embed.test.mjs scripts/local_web.py scripts/local_host.py tests/integration/test_webportal_bridge.py docs/M14-webportal-integration-bridge.md
git diff --cached --check
git diff --cached --stat
git commit -m "feat: add WebPortal integration bridge and staging contract"
git push -u origin feature/webportal-integration-bridge
```

Do not include generated live reports or local test records in that commit. M14 should be reviewed and the actual browser zoom check completed before it is frozen.
