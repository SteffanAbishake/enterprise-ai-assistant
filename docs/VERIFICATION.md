# Verification record

Verified on 2026-10-06 with Python 3.12 in the supplied development environment.

- `python -m pytest -q`: **14 passed**.
- `ruff check .`: **passed**.
- Python compile check for app, frontend and scripts: **passed**.
- Streamlit startup: tested using Streamlit AppTest, not a manual browser session.
- MCP: real local stdio subprocess call returned expected mock ownership data.
- API: exercised with HTTPX ASGI transport, including streamed event frames and follow-up memory.
- Failure injection: unavailable dense retrieval, unavailable language model and unavailable MCP.
- Security: role denial, restricted department denial, invalid input, invented citation rejection,
  session ownership separation and token-bucket replenishment.

Not verified: real OpenAI requests, real Pinecone ingestion/query, LangSmith trace arrival,
Docker image build/Compose execution, public GitHub CI or end-to-end browser interaction.
These require credentials, Docker or a published remote. No public demo video has been recorded.

Dependencies are frozen in `requirements.lock`. MCP is constrained to v1 because v2 renamed the
server API; the POC's actual subprocess path has been tested with the locked version.
