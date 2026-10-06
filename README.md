# Enterprise Knowledge Assistant

A chat application for finding answers in internal documents, such as runbooks, incident reports, policies and architecture notes. It shows the source passages alongside each answer so you can check where the information came from.

The included documents describe a fictional bank and its payment services. They let you try the application without uploading company data.

## How it works

The Streamlit interface sends questions to a FastAPI backend. A LangGraph workflow routes each request through search, analysis or a service lookup, then checks the response before returning it. The activity panel shows the steps as they happen.

There are two ways to run the application:

| Mode | What it does |
| --- | --- |
| Local | Searches the sample documents with BM25 and returns relevant excerpts. No OpenAI, Pinecone or LangSmith calls. |
| Live | Combines Pinecone embedding search with BM25, uses OpenAI to write an answer from the evidence, and sends execution traces to LangSmith. |

Local mode is useful for checking the interface, permissions and document search. It won't answer general questions about topics missing from the documents.

## Getting started

Use Python 3.12. Run the following commands from the repository root.

### Windows PowerShell

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
Copy-Item .env.example .env
```

### macOS or Linux

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
cp .env.example .env
```

Open `.env` and set three different login keys, each at least 16 characters long:

```dotenv
APP_MODE=local
VIEWER_KEY=replace-with-your-viewer-key
ANALYST_KEY=replace-with-your-analyst-key
ADMIN_KEY=replace-with-your-admin-key
LANGSMITH_TRACING=false
```

These keys control access to the application. Keep real credentials in `.env`, which is excluded from Git.

### Start the application

On Windows, start the backend:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

Leave that terminal running. Open a second terminal in the same folder and start the interface:

```powershell
.\.venv\Scripts\python.exe -m streamlit run frontend/chat.py --browser.gatherUsageStats false
```

On macOS or Linux, activate the virtual environment in each terminal and use `python` in place of `.\.venv\Scripts\python.exe`.

Open [the chat interface](http://localhost:8501) and enter one of your login keys. The [API documentation](http://localhost:8000/docs) is available on port 8000; that port does not have a homepage.

## Try it out

Leave the department set to **All allowed** and the date filter off for your first search.

- “What does the payment retry runbook recommend?”
- “Summarize payment outages and identify recurring root causes.” — requires an analyst or administrator key.
- “Who owns the payments service?” — requires an analyst or administrator key and `MCP_ENABLED=true`.

Viewers can search and chat. Analysts can also run the analysis and service catalog tools. Administrators can access restricted sample documents. Permissions are checked by the backend.

The service catalog is a local, read-only MCP server with fictional data. Restart the backend after changing its setting.

## Connect the live services

The live integrations are implemented, but still need verification with configured provider accounts.

1. Add your OpenAI, Pinecone and LangSmith credentials to `.env`.
2. Create a Pinecone dense vector index with **1536 dimensions** and **cosine** similarity for the default embedding model. Use an index compatible with the vectors API.
3. Set `PINECONE_HOST` to its HTTPS host and choose a dedicated `PINECONE_NAMESPACE`.
4. Set `APP_MODE=live` and `LANGSMITH_TRACING=true`.
5. Load the sample documents:

   ```powershell
   .\.venv\Scripts\python.exe -m scripts.ingest
   ```

6. Allow indexing to complete, restart the application and check a question against its sources. Use the displayed trace ID to find the run in LangSmith.

Live mode uses billable provider APIs. Check your account limits before enabling it. Trace inputs and outputs are hidden by default; only enable full payloads when the data is suitable for tracing.

## Tests

On Windows:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
```

GitHub Actions runs the tests and lint checks for pushes and pull requests.

## Docker

With Docker installed and `.env` configured:

```bash
docker compose up --build
```

Compose runs the backend and interface in separate containers, available locally on ports 8000 and 8501. The Docker configuration still needs an end-to-end verification run.

## Project structure

| Folder | Contents |
| --- | --- |
| `app/` | API, agent workflow, retrieval, permissions, memory and tools |
| `frontend/` | Streamlit chat interface |
| `data/` | Sample knowledge documents |
| `scripts/` | Pinecone ingestion |
| `tests/` | API, security, retrieval and failure-handling tests |
| `docs/` | Architecture and implementation notes |
| `.github/workflows/` | CI configuration |

## Current limits

Conversation history and rate limits are held in memory, so use one API worker. Restarting the backend clears the history. Recursive analysis is limited to the retrieved sections and does not guarantee a complete review of every document.

Responses are checked before their text is streamed to the interface. Citation checks confirm that references exist in the retrieved evidence; they do not prove that every claim is correct. Prompt-injection screening is also a partial defense, backed by fixed tools and server-side permissions.

For more detail, see [architecture and design decisions](docs/ARCHITECTURE.md).
