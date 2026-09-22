# Asta — A&A Engineering WebPortal AI Assistant

Asta answers questions about the A&A Engineering WebPortal using approved company documents. It is a WebPortal-focused retrieval-augmented generation (RAG) assistant, not a general chatbot. When evidence is insufficient, it says so or asks for clarification.

The core work through M16 has been accepted and is being moved to company staging. This README describes local use; Asta is not yet deployed in production.

## How Asta Works

```text
Knowledge: approved docs -> validation/extraction -> normalization/chunking -> BGE embeddings -> PostgreSQL/pgvector
Question: widget -> FastAPI -> guardrails/context/query understanding -> query embedding -> pgvector retrieval -> cross-encoder reranking -> RAG/Groq -> response
```

RAG retrieves relevant passages before asking the language model to answer. Adding approved documents updates searchable knowledge without retraining the language model.

## Main Technologies

| Area | Stack |
| --- | --- |
| Runtime/API | Python 3.12.4 target, FastAPI, Uvicorn |
| Storage | PostgreSQL, pgvector, SQLAlchemy, Psycopg, Alembic |
| Search | `BAAI/bge-small-en-v1.5` (384-dimensional embeddings), `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| Answers/tests | Groq, pytest, Node test runner |

## Prerequisites

Git, Python 3.12.x, PostgreSQL with pgvector, and a Groq API key are needed for live local use. Node is needed only for frontend tests. Cloning from Bitbucket requires company repository access and a configured SSH key.

## Quick Start

For a fresh Windows setup, run in PowerShell:

```powershell
git clone git@bitbucket.org:a-and-a-engineering-projects/ai-bot.git
cd ai-bot
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -c constraints-ci.txt
Copy-Item .env.example .env
```

Prepare PostgreSQL as described in Database Setup. Edit `.env` with your local database URLs and Groq API key before running migrations or starting Asta. Keep `.env` uncommitted. Then run:

```powershell
python -m alembic upgrade head
python -m scripts.check_runtime
python -m scripts.local_host
```

Open `http://127.0.0.1:8014/m14/`.

The clone command applies after the company repository migration. In an existing checkout, skip cloning and copy `.env.example` only if `.env` does not exist.

## Environment Configuration

Set your own values in `.env`:

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | Application PostgreSQL URL (`postgresql+psycopg://...`) |
| `TEST_DATABASE_URL` | Separate test database URL |
| `ALEMBIC_DATABASE_URL` | Optional migration override, such as for the test database |
| `GROQ_API_KEY` | Groq credential for live answers |
| `GROQ_MODEL`, `LLM_TEMPERATURE` | Answer model and temperature |
| `ASTA_CORS_ALLOWED_ORIGINS` | Exact allowed WebPortal origins |
| `KNOWLEDGE_ADMIN_API_ENABLED`, `KNOWLEDGE_ADMIN_TOKEN` | Internal knowledge administration gate |

The example file supplies the evaluated model settings. Embedding, reranking, and retrieval settings also have application defaults. Keep the evaluated settings for live evaluation runs.

## Database Setup

Create an application database and a separate test database in PostgreSQL. Recommended local development names are `asta_db`, `asta_test_db`, and application role `asta_app`; other names work because the connection URLs in `.env` are authoritative. Set the role's password locally and grant it access to the databases. In each database, run:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Then run:

```powershell
python -m alembic upgrade head
python -m scripts.check_runtime
```

The runtime check should confirm that configuration, database connectivity, and pgvector are ready. To migrate the test database, set `ALEMBIC_DATABASE_URL` to its URL in your local environment and run the migration command again. Do not point tests at the application database.

## Recommended: Run Asta in the Browser

Start the local browser integration fixture:

```powershell
python -m scripts.local_host
```

Open `http://127.0.0.1:8014/m14/`. This page simulates a host application; it is not the actual WebPortal. The first model load may download files and take longer if the models are not cached.

Optional: if the embedding and reranker models are already cached, set `$env:HF_HUB_OFFLINE='1'` and `$env:TRANSFORMERS_OFFLINE='1'` before starting Asta. Groq still requires normal network access.

## Other Run Options

For the API alone:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --loop asyncio:SelectorEventLoop
```

Open `http://127.0.0.1:8000/docs`. Health and readiness are at `http://127.0.0.1:8000/api/v1/health` and `http://127.0.0.1:8000/api/v1/ready`.

To ask from a terminal:

```powershell
python -m scripts.ask_asta "How do I use the WebPortal?"
```

## Knowledge Ingestion

Ingest approved `.md`, `.txt`, `.docx`, or `.pdf` files up to 20 MB each. PDF extraction requires selectable text; scanned PDFs have no OCR support. For a first ingestion, copy approved files into `approved-docs` between the first and second commands:

```powershell
New-Item -ItemType Directory -Force .\approved-docs
python -m scripts.ingest_directory .\approved-docs --dry-run
python -m scripts.ingest_directory .\approved-docs
python -m scripts.knowledge_status
```

For one file, use `python -m scripts.ingest_directory --file .\approved-docs\guide.pdf`. Folder ingestion is non-recursive unless `--recursive` is supplied. Documents are tracked by SHA-256 and version; unchanged content is treated as a duplicate. New knowledge does not require model retraining. The older `ingest_document` and `index_embeddings` scripts remain available for legacy workflows.

## Testing and Evaluation

Run from the repository root with the virtual environment active. The full suite is not needed just to open the widget.

### Basic verification

```powershell
python -m pip check
python -m scripts.check_startup
python -m scripts.check_repository_safety
python -m scripts.check_runtime
```

### Full development test suite

Python tests require the configured test database. Node is needed for frontend tests.

```powershell
New-Item -ItemType Directory -Force .cache | Out-Null
python -m pytest -q -p no:cacheprovider --basetemp=.cache/local-tests
node --test frontend/tests/*.test.mjs
```

### AI evaluation

Live evaluation requires approved indexed knowledge, the models, and Groq access.

```powershell
python -m scripts.run_evaluation
python -m scripts.run_evaluation --cases data/evaluation/m15_robustness_cases.json
```

## Knowledge Administration

M16 includes a protected knowledge administration API for controlled internal management. It is disabled by default. Enabling it requires `KNOWLEDGE_ADMIN_API_ENABLED` and a token sent in `X-Asta-Admin-Token`; use it only in an approved internal setting until trusted WebPortal authorization is integrated.

## Security Notes

- Never commit `.env`, credentials, or other secrets.
- Browser-supplied roles are not trusted authorization.
- Prompt-injection guardrails check questions and retrieved content.
- Telemetry avoids raw user and document content.
- CORS uses exact origins; the administration API is disabled by default.

## Current Limitations / Next Steps

Staging will cover WebPortal authentication, ownership, and permission integration and incremental knowledge ingestion. Scanned PDF OCR is not implemented, ingestion is synchronous, and the feedback UI is not wired yet.

Staging observations will guide query, typo, retrieval, and widget improvements. Production load testing, rate limiting, monitoring, and deployment hardening remain future work.

## Development Workflow

`main` is the accepted baseline. Work on feature branches, run tests and evaluation, open a reviewed pull request, then merge to `main`. After migration, the company Bitbucket repository will be the canonical development repository.
