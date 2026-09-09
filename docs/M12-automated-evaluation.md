# M12 — Automated Evaluation & Quality Baseline

## 1. Status, baseline and scope

The M12 topic-reset correction is applied on `feature/automated-evaluation` in
`D:\Projects\Asta-WebPortal-AI`. **Live acceptance is PASS: 129 Python tests,
10 Node tests, all 17 live cases, CLI exit 0**. The final run uses the existing virtual
environment, configured database, cached models and real Groq service.

| Baseline | Value |
| --- | --- |
| Repository | `D:\Projects\Asta-WebPortal-AI` |
| Main / HEAD commit | `1dbef3bb5020cea8bc28a3843a22fb202e95ef3a` |
| Feature branch | `feature/automated-evaluation` |
| Branch creation | User created it from refreshed main before implementation |
| Pre-change regression baseline | 71 Python tests; 10 Node tests passed |
| Final regression baseline | **129 Python tests; 10 Node tests passed** |
| New Python checks | 58 (including parameterized schema/metric cases) |
| Frozen M0–M11 changes | None |
| Database migration / dependency additions | None |

Only read-only Git commands were used during implementation after the user's branch handoff.
Nothing was staged, committed, pushed, merged or deployed. Existing services, model implementations,
prompts, guardrails, sanitizer, API, widget and persistent-conversation architecture are unchanged.

## 2. File inventory

All paths below are relative to the repository root. The files already exist; do not recreate them.

| Created file | Purpose |
| --- | --- |
| `app/evaluation/__init__.py` | Evaluation package boundary |
| `app/evaluation/cases.py` | Versioned Pydantic schema, strict validation and JSON loader |
| `app/evaluation/metrics.py` | Normalized term/section matching, per-case retrieval metrics and aggregation |
| `app/evaluation/results.py` | Explicit result, observation, regression, pipeline-summary and report DTOs |
| `app/evaluation/evaluators.py` | Retrieval and structural answer assertions |
| `app/evaluation/runner.py` | Injected runner, transparent call counters, conversation sequencing and quality gates |
| `app/evaluation/live.py` | Existing real service composition, corpus fingerprint and rollback-only conversation scope |
| `app/evaluation/regressions.py` | Mandatory Python/Node subprocess gates with structured counts |
| `app/evaluation/reporting.py` | Summary-only JSON, redaction and atomic replacement of reports |
| `scripts/run_evaluation.py` | CLI validation, regression execution, live run, summary and exit code |
| `data/evaluation/golden_cases.json` | 17 curated cases, including one five-step conversation |
| `tests/evaluation/test_cases.py` | Golden parsing, invalid data, duplicate keys/IDs and documented ambiguity |
| `tests/evaluation/test_metrics.py` | Rank detection, Top-1, Recall@K, RR, MRR and normalization |
| `tests/evaluation/test_evaluators.py` | Required/any-of/forbidden assertions, source/model/grounding, bypasses and report exclusion |
| `tests/evaluation/test_runner.py` | Real RAG/guardrail/context components with fake boundaries, pass/fail gates and safe error codes |
| `tests/evaluation/test_reporting_cli.py` | Serialization, secret safety, CLI success, deliberate failure and runtime failure |
| `tests/evaluation/test_regressions.py` | Regression subprocess success/failure/skip/missing-runtime handling |
| `tests/evaluation/test_persistence.py` | Real test-DB conversation history and rollback on success and failure |
| `docs/M12-automated-evaluation.md` | This implementation guide and review runbook |

Modified file: `.gitignore` adds `data/evaluation/results/`. Golden cases remain versionable;
generated JSON reports are ignored. The existing `.cache/` ignore covers temporary test files.
Existing `tests/evaluation/__init__.py` is reused unchanged.

Generated, ignored artifacts:

- `data/evaluation/results/m12-baseline.json`: first completed live run, FAIL on Groq connectivity.
- `data/evaluation/results/m12-final.json`: historical validation with classified connection failures.
- `data/evaluation/results/m12-topic-reset-correction-checkout.json`: final corrected live checkout run, PASS.
- `.cache/`: repository-local pytest temporary files. CLI regression temporary directories and
  their JUnit data are removed after regression execution.

## 3. Evaluation architecture

The CLI loads a validated `CaseSuite`, runs mandatory regressions, then composes the existing
`KnowledgeRetrievalService`, shared embedding service, shared reranker and shared Groq client.
Existing `RAGService` and `AstaService` execute the same grounding, sanitizer and guardrail behavior
as serving code. Evaluation wraps the search, answer and generate methods only to count calls;
arguments and results are delegated unchanged. No second inference implementation is introduced.

`runner.py` accepts injected services, so offline tests can substitute retrieval and LLM boundaries.
These tests still exercise the real RAG, guardrails, context builder and ConversationService.
The live composition uses the actual SQL repository, pgvector search, cross-encoder reranking and
configured Groq client. API HTTP transport and browser behavior remain covered by their existing
regressions, not duplicated in this service-level evaluator.

Category evaluators produce explicit DTOs, not dictionaries copied from settings or service
objects. The report includes run ID, UTC time, baseline commit when read-only Git works, golden-file
SHA-256, corpus SHA-256, safe model/retrieval settings, per-case assertions and aggregate gates.
The corpus fingerprint covers active ready indexed chunk IDs, sections, content, document content
hashes and embedding model names; it does not hash embedding vector bytes or model-weight files.
Corpus content itself is not written to the report.

Failures are closed: a missing case, missing category, empty result, failed assertion, service error,
failed/skipped regression or missing regression runtime cannot produce PASS. Per-case service
exceptions become finite diagnostic codes, never raw exception messages. Partial completed
conversation steps are retained if a later step raises.

## 4. Golden-case format and extension

The JSON root requires `schema_version: 1`, a name and cases. All five categories must be present.
Unknown keys, duplicate JSON keys, duplicate IDs, invalid category values, blank strings, wrong
types, nonpositive K, rank beyond K, contradictory terms and logically inconsistent expectations
are rejected before live work. Generated supported prose cannot have an exact-answer assertion.
Every conversation step must declare its expected context state.

Example supported case:

```json
{
  "id": "answer-apn",
  "category": "supported_answer",
  "query": "Where can I enter parcel information for the project location?",
  "expected_section": "APN Parcel Number",
  "expected_topic": "APN Parcel Number",
  "required_terms": ["location"],
  "required_any_of": [["APN", "Parcel Number"]],
  "forbidden_terms": ["Assessor's Parcel Number", "Assessors Parcel Number", "Assessor Parcel Number"],
  "expected_grounded": true,
  "expected_model": true,
  "expected_sources": true
}
```

`expected_section` is the exact section label after normalization; `expected_topic` is its
human-readable semantic description. The evaluator does not infer semantic equivalence between
unrelated section titles. Retrieval cases additionally require `k` and default `max_rank` to 1.
A larger rank requires a nonempty `ambiguity_reason` and cannot exceed K. The current curated
cases all require rank 1; **no ambiguity exception or weakened metric is used**.

For future company documentation:

1. Ingest/index approved documents using the existing ingestion pipeline.
2. Inspect actual indexed section labels and authoritative content.
3. Add paired retrieval and supported-answer cases for the new feature, using unique stable IDs.
4. Define required facts as terms or any-of groups, and known unsupported claims as forbidden terms.
5. Add unsupported/guardrail/context cases where they exercise a meaningful boundary.
6. Run offline tests and the complete live CLI; review every failed assertion against the corpus.
7. Document a real ambiguity before changing a rank expectation. Do not edit cases merely to hide
   an observed defect. If a previously unsupported feature becomes documented, replace or revise
   that case deliberately; record the changed baseline and golden-file hash.

Term checks use NFKC normalization, case folding and word sequences. Punctuation, apostrophe style
and repeated whitespace do not matter. Word boundaries prevent APN matching a substring such as
“apnea”. Plurals and paraphrases are explicit data choices; matching does not use a semantic judge.

## 5. Metrics and quality gates

Retrieval evaluates the existing **final reranked, thresholded list**. Current settings are candidate
Top-K 8, final K 4 and minimum rerank score 0.5. Cases request K=4; the live CLI rejects a case whose
K exceeds the configured final window. Returning fewer than four results is valid after thresholding.

- Top-1 Accuracy = cases with the expected section at rank 1 / all retrieval cases.
- Recall@K = 1 when the expected relevant topic appears within K, otherwise 0; report the macro mean.
  This is binary topic recall, not recall of every relevant chunk in a document collection.
- Reciprocal Rank = 1/r for the first expected section, or 0 when absent.
- MRR = mean reciprocal rank across all retrieval cases.

Reports retain every returned rank, chunk ID, section, vector score and rerank score, plus expected
section rank, Top-1, Recall@K and RR. Empty results contribute zero; they are never dropped.

Supported-answer gates require expected grounding, model presence, sources, expected source section,
all required terms, one term from each any-of group and no forbidden terms. The Create New Project
case covers unsupported buttons, field names, navigation, validation, permissions, roles, workflows,
automatic actions and statuses through explicit forbidden phrases. APN cases reject unsupported
acronym expansions. The topic-reset step permits approved APN / Parcel Number overlap while
requiring context false and retaining every unsupported-claim forbidden, including the expansion.

Unsupported cases must exactly match the approved insufficient-information response, have no
model/sources/token usage, invoke retrieval and RAG once, and invoke the LLM zero times. Guardrails
must exactly match their fixed responses and invoke retrieval, RAG and LLM zero times. Null usage
is required on bypasses; a spurious token value of zero still fails the existing null-usage contract.

All required cases and all regressions must pass. Forbidden claims have zero tolerance among
evaluated answers. There is no latency or token-count gate. Missing generation is a failed case,
not evidence of zero hallucinations. Exit status is 0 only for all-green gates; otherwise it is 1.
Tests deliberately introduce a failing rank assertion and verify that the actual CLI returns 1.

## 6. Conversation persistence and isolation

The golden sequence is:

1. Parcel-location question → grounded APN answer, context false.
2. “Can you explain that option?” → APN continuation, context true, no acronym expansion.
3. “How does Create New Project work?” → new topic, context false, approved title information,
   approved APN / Parcel Number overlap allowed; unsupported acronym expansion forbidden.
4. “Tell me a joke.” → fixed WebPortal redirect, context false, zero RAG/LLM calls.
5. Injection request → fixed block, context false, zero RAG/LLM calls.

Live evaluation starts an existing ConversationService inside a SQL savepoint. Its records carry
`page_context` identifying M12 and rollback-only persistence; message request IDs identify case/step.
The normal repository flushes messages and subsequent turns read SQL history. The evaluator rolls
back the savepoint in `finally` and verifies that the conversation no longer exists. The surrounding
session is also rolled back. It does not commit or delete unrelated records. No live evaluation
conversation is retained, including after failed generation.

The new database tests verify four persisted messages during a two-turn context sequence and zero
conversation/message rows afterward, on both normal completion and an injected exception. This
tests transactional persistence and cleanup; it does not claim cross-process committed-session
coverage. Existing repository/API regression tests remain intact.

## 7. Exact commands

From PowerShell in the repository root:

```powershell
Set-Location D:\Projects\Asta-WebPortal-AI
New-Item -ItemType Directory -Force .cache | Out-Null
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp=.cache/m12-review-tmp
node --test frontend/tests/chat-client.test.mjs
```

Expected: 129 Python tests and 10 Node tests pass. Ordinary tests do not call Groq or download
models. Existing database integration tests and the new persistence checks require the configured
local test database. The repository-local temp option avoids this environment's denied default
`pytest-of-SOURA` directory; no application or test configuration was changed to work around it.

Run the real evaluator (includes both mandatory regression suites automatically):

```powershell
.\.venv\Scripts\python.exe -m scripts.run_evaluation
```

The default report is `data/evaluation/results/<run-id>.json`. To reproduce the final invocation
using the already-cached, unchanged models without Hugging Face metadata requests:

```powershell
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
.\.venv\Scripts\python.exe -m scripts.run_evaluation --report data/evaluation/results/m12-topic-reset-correction-checkout.json
$LASTEXITCODE
```

These environment variables affect model-cache lookup only. Groq must still be reachable over
HTTPS. They do not replace inference with fakes or change model weights/settings. Remove them in
that shell if future model downloads are needed. First online model initialization stalled in this
restricted environment; the cached-model run completed real retrieval successfully.

Use a new report filename to preserve previous runs. An explicitly reused report path is replaced
atomically. Custom cases use `--cases path/to/cases.json`; the complete category and regression
gates remain mandatory. There is no option to skip failed categories and still claim M12 PASS.

Inspect the safe report:

```powershell
$m12Report = Get-Content data/evaluation/results/m12-topic-reset-correction-checkout.json -Raw | ConvertFrom-Json
$m12Report.status
$m12Report.regressions | Format-Table
$m12Report.retrieval_metrics
$m12Report.category_summary
$m12Report.results | Select-Object id,passed,error_code,checks | Format-Table
```

## 8. Recorded live results — 9 September 2026

Final validation ran from `D:\Projects\Asta-WebPortal-AI` after applying the correction.
Run ID: `863ab3ac-9f6b-48ab-b87a-8147e38fa456`.
Started at `2026-09-09T16:27:20.210978+00:00`.
Report: `data/evaluation/results/m12-topic-reset-correction-checkout.json`.
The CLI ran both complete mandatory regression suites: **129 Python / 10 Node passed**.

| Category | Total | Passed | Failed |
| --- | ---: | ---: | ---: |
| Retrieval | 5 | 5 | 0 |
| Supported grounded answers | 5 | 5 | 0 |
| Unsupported knowledge | 2 | 2 | 0 |
| Standalone guardrails | 4 | 4 | 0 |
| Persisted conversation sequence | 1 | 1 | 0 |
| Overall | 17 | 17 | 0 |

**Overall PASS; process exit code 0.** Top-1 Accuracy, Recall@4 and MRR are all **1.000**.
The reset observation is grounded, non-contextualized, and uses `openai/gpt-oss-120b`.
Sources: `Create New Project`, `Building Address`, an untitled source.
Every reset assertion passes. Both conversation guardrails have zero retrieval/RAG/LLM calls;
`sequence_complete=true`, `cleanup_verified=true`, and `error_code=null`.

Golden SHA-256: `1a8f29cfaddc03fdcc6872eeaf0750605bf3231b4fab49d5eaf672059e2f0c22`.
Corpus SHA-256: `901ec9299fdbd3f004eebe64dd4d5c10c68b22bb8d0e75ab80a9db1b9885286b`.
The corpus hash is unchanged from the historical run. Baseline commit:
`1dbef3bb5020cea8bc28a3843a22fb202e95ef3a`.

## 9. Performance and token observations

Complete CLI time, including mandatory regressions: **19.590 seconds**.
Persisted conversation: **4.346 seconds**. Explicit reset: **2.411 seconds**,
925 prompt tokens, 264 completion tokens, 1,189 total tokens.
These are observations from this run, not performance gates. Bypasses retain null model/token usage.

## 10. Reproduced evaluator false positive and frozen-module review

The original local acceptance report `m12-local-acceptance-2.json` recorded 16/17 cases passing.
Only reset checks `forbidden_term_52` (`APN`) and `forbidden_term_53` (`Parcel Number`) failed;
its context, grounding, model/source, sequence and cleanup checks passed. Those overlapping terms
are approved Building Address/Create New Project knowledge and do not establish stale context.

The correction removes exactly those two terms from this conversation step. It preserves the
original first 52 unsupported-claim forbiddens and `Assessor's Parcel Number` (formerly index 54,
now index 52). All other cases, context expectations, evaluator logic and M0–M11 code are unchanged.

The new evaluator regression passes a sourced overlapping answer with context false, rejects the
same answer with context true, and rejects an added unsupported expansion with context false.
Running that regression against the original golden data reproduced its failure (pytest exit 1).
The corrected data passes the full suite. The existing real RAG/context/guardrail runner fixture
also now retrieves approved project content containing APN / Parcel Number, exercising the complete
continuation-to-reset sequence with overlap rather than only isolated answer assertions.

Earlier outbound Groq failures are historical; real generation succeeded in the corrected run.
An initial review-copy test invocation had 19 setup errors due to a missing `.cache` parent;
creating that output directory resolved them. The final CLI reran both full suites successfully.
No application code, prompts, model settings, migrations, dependencies or corpus data were modified.
The validated patch was applied to the original checkout after filesystem access was enabled.
Nothing was staged, committed, pushed, merged or deployed.

## 11. Report security and example safe summary

JSON reports use explicit DTOs and an allowlisted pipeline summary. They exclude raw Asta answers,
chunk content, prompt templates, internal system text, arbitrary settings/repository objects,
source metadata and exception strings. Safe assertion identifiers show which rule failed; the
golden case supplies its meaning. Source titles and queries are retained for audit, with redaction
at serialization for configured sensitive values, credential-like tokens and connection URLs.
Temporary report replacement prevents partially serialized JSON becoming the final report.

Terminal output is limited to case IDs, category counts, numeric metrics and finite failure codes.
Third-party live logging/stdout/stderr is suppressed. Regression subprocess output is captured;
only structured JUnit/TAP counts enter the JSON report. Do not enable debug logging or add raw
settings/exception dumps to investigate failures.

Example summary of the actual final report:

```json
{
  "status": "PASS",
  "retrieval_metrics": {
    "cases": 5,
    "top1_accuracy": 1.0,
    "recall_at_k": 1.0,
    "mrr": 1.0
  },
  "supported_answer": {"total": 5, "passed": 5, "failed": 0},
  "conversation": {"total": 1, "passed": 1, "failed": 0}
}
```

Automated report tests cover credential-shaped strings, URLs, configured secret values, hidden
text in generated answers, rejection of arbitrary credential settings and safe CLI exceptions.
The final generated report was separately checked against configured secrets and internal system
prompt text; no matches were present. Reports should remain local ignored artifacts. Source section
labels and queries may describe future company knowledge even when they contain no credentials.

## 12. Known limitations

- The corpus is small synthetic development knowledge, not comprehensive company documentation.
- Five primary retrieval questions are a curated baseline, not a statistical estimate of all queries.
- Term rules are deterministic lexical checks. They do not prove complete factual entailment, and
  explicit forbidden lists cannot detect every possible invented claim or paraphrase. Negative
  statements containing a forbidden phrase also fail conservatively. Update reviewed case data
  as the corpus grows; no LLM-as-judge is used.
- Groq temperature 0.0 does not guarantee identical hosted-model prose across time. Structural
  assertions avoid full-answer matching, but live model/version/provider changes can affect results.
- Persistence evaluation uses SQL flush/read within a rollback-only transaction. It intentionally
  leaves no durable conversation and does not test a multi-client committed conversation lifecycle.
- The CLI enforces the specified frozen model/device/temperature baseline. Deliberate future model
  migrations require an explicit baseline revision rather than silent evaluation against another model.
- Ordinary tests require the existing local test PostgreSQL database, but never internet/Groq/HF downloads.
- No staging, production WebPortal integration, authentication redesign, CI/CD expansion or deployment
  is included. No Ruff package was installed; it is absent from the existing virtual environment.

## 13. Git review

Run these read-only commands:

```powershell
git status --short
git diff --stat origin/main
git diff --check
```

Expected final status:

```text
 M .gitignore
?? app/evaluation/
?? data/evaluation/
?? docs/M12-automated-evaluation.md
?? scripts/run_evaluation.py
?? tests/evaluation/test_cases.py
?? tests/evaluation/test_evaluators.py
?? tests/evaluation/test_metrics.py
?? tests/evaluation/test_persistence.py
?? tests/evaluation/test_regressions.py
?? tests/evaluation/test_reporting_cli.py
?? tests/evaluation/test_runner.py
```

`git diff --stat origin/main` reports `.gitignore | 5 ++++-` and one changed file, four insertions,
one deletion (including the existing missing-final-newline normalization). **Untracked additions do
not appear in this unstaged diff stat**; review the full inventory in section 2. Nothing was staged
to manufacture a larger diff. `git diff --check` returns 0 with no whitespace errors; Git may print
its existing Windows LF-to-CRLF advisory for `.gitignore`.

## 14. Future manual commit/push commands — not executed

After architecture review and successful live acceptance, the user can manually run:

```powershell
git add .gitignore app/evaluation data/evaluation/golden_cases.json scripts/run_evaluation.py tests/evaluation/test_cases.py tests/evaluation/test_metrics.py tests/evaluation/test_evaluators.py tests/evaluation/test_runner.py tests/evaluation/test_reporting_cli.py tests/evaluation/test_regressions.py tests/evaluation/test_persistence.py docs/M12-automated-evaluation.md
git diff --cached --check
git diff --cached --stat
git diff --cached
git commit -m "feat: add automated evaluation and quality baseline"
git push -u origin feature/automated-evaluation
```

Do not add generated report files. No commit, push, merge or deployment was performed by this task.
