# Enterprise Knowledge Assistant

An explainable AI Lead assessment POC for a fictional **Demo Bank**. Built with Python 3.12,
FastAPI, Streamlit and LangGraph. Includes role-controlled retrieval and tools, recursive batch
analysis, citations, activity streaming, session memory, rate limiting, tests and GitHub CI.

**Status:** local functionality is implemented; live OpenAI/Pinecone/LangSmith integrations need
credentials and a verification run. Public GitHub publishing and the demo recording are separate
submission steps. See [coverage and limitations](docs/REQUIREMENTS.md).

## Run locally — no provider API calls

Create a Python 3.12 virtual environment and install dependencies:

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS / Linux instead:
# source .venv/bin/activate
python -m pip install -r requirements.lock
```

Copy `.env.example` to `.env`. Set three distinct API keys of at least 16 characters. They are local
login secrets, not OpenAI keys. Keep `APP_MODE=local` and `LANGSMITH_TRACING=false`.
Generate keys if desired with `python -c "import secrets; print(secrets.token_urlsafe(24))"`.

Start the API from the repository root:

```bash
python -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

In a second terminal using the same environment:

```bash
python -m streamlit run frontend/chat.py --browser.gatherUsageStats false
```

Open http://localhost:8501 and enter a configured viewer, analyst or administrator key. API docs:
http://localhost:8000/docs. Local mode uses BM25 and evidence excerpts, **not** a simulated LLM or
simulated vector database. No cloud resources are provisioned automatically.

## Live mode

1. Supply OpenAI, Pinecone and LangSmith keys in `.env`; do not commit this file.
2. Create a Pinecone **dense vector index**, dimension **1536**, metric **cosine**.
   Use the vectors API index type, not an integrated-embedding or documents API index.
3. Set its HTTPS `PINECONE_HOST`, a dedicated namespace, `APP_MODE=live` and `LANGSMITH_TRACING=true`.
4. Run `python -m scripts.ingest` once, allow indexing to complete, then start/restart the API and UI.
5. Verify retrieved evidence, then locate the displayed trace ID in your LangSmith project.

Live mode incurs provider usage. Set provider-side budgets before running; there is no universal
hard spending cap in this application. Queries have bounded results, recursion and output tokens.
Changing embedding models may require a different index dimension and re-ingestion.

The default trace configuration hides payloads; enable them only for synthetic data when recording
the assessment. To demonstrate MCP, set `MCP_ENABLED=true` and restart. MCP uses a local read-only
subprocess server with fictional service data.

## Tests and containers

```bash
python -m pytest -q
ruff check .
docker compose up --build
```

Compose reads the local `.env` and exposes UI/API on loopback only. Use one API worker: rate limits
and session memory are intentionally in-process. The lock file records the verified Python environment.

## Project map

| Directory | Purpose |
|---|---|
| `app/` | API, models, graph, retrieval, providers, memory, permissions and tools |
| `frontend/` | Streamlit chat and activity panel |
| `data/` | Fictional incidents, runbook, policy, architecture and restricted HR example |
| `scripts/` | Explicit live Pinecone ingestion |
| `tests/` | Authorization, filtering, citations, memory, rate limits and failure tests |
| `docs/` | Architecture, requirements, GitHub workflow and 45-minute demo script |
| `.github/workflows/` | Automated lint and test checks |

## Repository and assessment delivery

Follow [GitHub workflow](docs/GITHUB_WORKFLOW.md) to restore the bundled Git history and create one
public repository. Use feature branches and pull requests for subsequent work.

- [Architecture and trade-offs](docs/ARCHITECTURE.md)
- [Assessment coverage](docs/REQUIREMENTS.md)
- [Demo recording script](docs/DEMO_SCRIPT.md)

Demo video URL: **add after recording and publishing**.
Live trace verification: **pending credentials and execution**.

AI tools assisted implementation. The commit history preserves this work transparently. Review the
code and be prepared to explain the security boundaries, retrieval design and POC limitations.
