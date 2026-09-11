# Asta-WebPortal-AI
AI knowledge assistant for A&amp;A Engineering's WebPortal using Retrieval-Augmented Generation, semantic retrieval, Groq-powered conversational intelligence, strict domain guardrails, contextual conversation management, and production-oriented API architecture.

Asta answers from approved WebPortal documentation. Missing evidence produces a deterministic
insufficient-information response; unclear questions ask for clarification. The surrounding local
host page is a demo fixture. Real WebPortal authentication and staging integration remain future work.

The frozen stack is Python 3.12.4, FastAPI, async SQLAlchemy/Psycopg 3, Alembic,
PostgreSQL 18.6 with pgvector 0.8.6, normalized 384-dimensional BGE embeddings,
cosine retrieval, MiniLM cross-encoder reranking, and Groq `openai/gpt-oss-120b` at temperature 0.0.
Security checks precede conservative query interpretation, conversation context, retrieval,
evidence filtering and grounded generation. Raw user messages are stored; interpreted queries are transient.

## Local setup

Use Python **3.12.4** and Node **24.19.0**. From the repository root on Windows:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -c constraints-ci.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Copy the example only for a new checkout; preserve an existing `.env`. Set `DATABASE_URL` and
`TEST_DATABASE_URL` to separate local databases using `postgresql+psycopg://` URLs, and provide
`GROQ_API_KEY` locally for live answers. Keep the example's frozen model/temperature/retrieval values.
Never put credentials in source, shell history, screenshots or reports. `.env` is ignored.

Install PostgreSQL 18.6 and pgvector 0.8.6. Create a local role `asta_app`, an application database
`asta_db`, and a separate disposable test database `asta_test_db`, owned by that role. Assign a
local password using your database administration tool. As an administrator, execute
`CREATE EXTENSION vector;` in both databases. Then apply the existing migrations to each:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
# Set ALEMBIC_DATABASE_URL to your local test database URL using your secure environment setup.
.\.venv\Scripts\python.exe -m alembic upgrade head
Remove-Item Env:ALEMBIC_DATABASE_URL
```

Ordinary tests use the test database with fake model/provider implementations. They do not need
Groq or Hugging Face downloads. Live evaluation needs the approved indexed corpus, cached frozen
models and a local Groq credential. Initial model caching requires network access as part of setup.

## Run and ingest

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --loop asyncio:SelectorEventLoop --no-access-log
# Reusable widget and M14 local host fixture (separate command):
.\.venv\Scripts\python.exe -m scripts.local_host
```

On Linux use `python` in the activated environment and omit the Windows selector-loop argument.
The fixture is at `http://127.0.0.1:8014/m14/`; standalone widget at `/m11/` on the fixture server.
The normal app entry does not expose fixture files. API documentation is at `/docs`.

Knowledge ingestion and indexing retain their existing CLI contracts:

```powershell
.\.venv\Scripts\python.exe -m scripts.ingest_document --help
.\.venv\Scripts\python.exe -m scripts.index_embeddings --help
.\.venv\Scripts\python.exe -m scripts.search_knowledge --help
```

Ingest approved documents, then index the new active version before querying. Use CLI help for
the exact file/document-ID arguments. Do not ingest unapproved material into the demo corpus.

Endpoints: `GET /api/v1/health`, `GET /api/v1/ready`,
`POST /api/v1/chat/conversations`, and `POST /api/v1/chat/conversations/{id}/messages`.
Health checks the application; readiness checks its database/pgvector dependencies.

## Validation and engineering workflow

```powershell
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp=.cache/local-tests
node --test frontend/tests/*.test.mjs
.\.venv\Scripts\python.exe -m scripts.check_startup
.\.venv\Scripts\python.exe -m scripts.check_repository_safety
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m scripts.check_runtime
# Live acceptance only, never ordinary CI:
.\.venv\Scripts\python.exe -m scripts.run_evaluation
.\.venv\Scripts\python.exe -m scripts.run_evaluation --cases data/evaluation/m15_robustness_cases.json
```

Workflow: feature branch → local validation → push → pull request → CI gates → review → merge main.
The two CI checks are **Python and database quality** and **JavaScript quality**.
Recommend requiring both checks, an independent review, resolved review conversations and no direct
pushes to main. Repository administrators must configure those protections; documentation does not enable them.

The runtime version remains **0.1.0** in `app/core/constants.py`. Future releases use semantic
versioning and reviewed `vMAJOR.MINOR.PATCH` tags on accepted main commits. Update the matching
`pyproject.toml` metadata in the same release PR; startup validation checks equality. Consolidating
the two sources is deferred to packaging work, avoiding runtime dependence on a repository file.
Milestone numbers are not release versions. Record accepted changes, migration/configuration
requirements and known limitations in release notes before tagging. No automatic release or deployment exists.


