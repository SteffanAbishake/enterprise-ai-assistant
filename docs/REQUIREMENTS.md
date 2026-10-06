# Assessment coverage

| Requirement | Implementation / verification |
|---|---|
| Streamlit chat, history, activity | `frontend/chat.py`; local UI smoke check, API integration tests |
| Async FastAPI, retrieval, tools | `app/main.py`, `retrieval.py`, `tools.py` |
| LangGraph specialized agents | Supervisor, retrieval, research, response, tools, validation nodes |
| RLM concept | Bounded recursive batch analysis; deterministic plan; simplified rather than full RLM |
| Hybrid search | Live Pinecone dense + local BM25 + reciprocal rank fusion |
| Pinecone namespaces, metadata, attribution | REST adapter and ingestion command; real credentials required to verify live |
| Session memory | Owner-scoped bounded in-process history; tested |
| Knowledge / Python / MCP tools | Server-authorized search, fixed analytics, stdio mock service catalog |
| LangSmith | Required configuration in live mode; actual traces require live run |
| Prompt injection | Input/content patterns, untrusted-data prompt, fixed tools; incomplete defense acknowledged |
| Citation guardrail | Schema + evidence ID membership; semantic entailment is not proven |
| RBAC | Hardcoded identities with distinct configured keys; role tests |
| Token bucket | Per predefined identity, configurable capacity/refill; refill test |
| Error handling | Retrieval fallback, model fallback, MCP warning, timeouts, invalid requests |
| Docker / CI | Compose and GitHub Actions included; Docker build needs local verification |
| Public source repository | Prepared source + Git history; GitHub publication still required |
| Architecture diagram | Mermaid in `docs/ARCHITECTURE.md` |
| Public 45-minute demo | Recording plan in `docs/DEMO_SCRIPT.md`; recording/upload still required |
| Bonus features | Containers included; HITL, long-term memory and feedback workflow deferred |

This is an explainable POC with production-oriented boundaries, not a claim of a fully production-ready
banking assistant. Prioritize real provider verification and being able to explain every module before submission.
