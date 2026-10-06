import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse
from langsmith import tracing_context

from app.config import Settings
from app.graph import build_graph
from app.memory import SessionMemory
from app.models import ChatRequest
from app.providers import Providers
from app.retrieval import Retrieval
from app.security import TokenBucket, authenticate, validate_input

logger = logging.getLogger("assistant")
logging.basicConfig(level=logging.INFO, format="%(message)s")


def create_app(settings=None):
    settings = settings or Settings()
    tracing = settings.app_mode == "live" and settings.langsmith_tracing
    if tracing:
        os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
        os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
        os.environ.setdefault("LANGSMITH_HIDE_INPUTS", "true")
        os.environ.setdefault("LANGSMITH_HIDE_OUTPUTS", "true")
    providers = Providers(settings)
    retrieval = Retrieval(settings, providers)
    graph = build_graph(settings, retrieval, providers)
    memory = SessionMemory()
    limiter = TokenBucket(settings.token_capacity, settings.token_refill_per_second)

    @asynccontextmanager
    async def lifespan(app):
        yield
        await providers.close()

    app = FastAPI(title="Enterprise Knowledge Assistant", lifespan=lifespan)
    app.state.providers = providers
    app.state.retrieval = retrieval

    async def current_user(x_api_key: str = Header(default="")):
        user = authenticate(x_api_key, settings)
        await limiter.take(user.id)
        return user

    @app.get("/health")
    async def health():
        return {"status": "ok", "mode": settings.app_mode, "tracing_configured": tracing}

    @app.post("/chat")
    async def chat(request: ChatRequest, user=Depends(current_user)):
        validate_input(request.message)
        if request.since and request.until and request.since > request.until:
            raise HTTPException(422, "Start date must precede end date")
        if request.department and request.department not in user.departments:
            raise HTTPException(403, "Department access denied")
        trace_id = str(uuid4())

        async def stream():
            started = time.monotonic()
            outcome = "completed"
            try:
                async with memory.session(user.id, request.session_id) as history:
                    final = None
                    yield encode(
                        {
                            "type": "activity",
                            "node": "memory",
                            "status": "loaded",
                            "turns": len(history),
                            "trace_id": trace_id,
                        }
                    )
                    with tracing_context(enabled=tracing):
                        async with asyncio.timeout(90):
                            async for item in graph.astream(
                                {"user": user, "request": request, "history": list(history)},
                                config={
                                    "run_id": trace_id,
                                    "run_name": "knowledge_conversation",
                                    "metadata": {"role": user.role, "mode": settings.app_mode},
                                    "recursion_limit": 16,
                                },
                                stream_mode="custom",
                            ):
                                if item["type"] == "answer":
                                    final = item
                                yield encode(item)
                    if final:
                        history.append({"role": "user", "content": request.message})
                        history.append({"role": "assistant", "content": final["text"][:4000]})
                        yield encode({"type": "activity", "node": "memory", "status": "updated"})
                    yield encode({"type": "done", "trace_id": trace_id})
            except HTTPException as exc:
                outcome = "denied"
                yield encode({"type": "error", "code": exc.status_code, "message": exc.detail})
            except asyncio.CancelledError:
                outcome = "cancelled"
                raise
            except TimeoutError:
                outcome = "timeout"
                yield encode(
                    {
                        "type": "error",
                        "code": 504,
                        "message": "Request timed out; try a narrower question.",
                    }
                )
            except Exception:
                outcome = "failed"
                yield encode(
                    {
                        "type": "error",
                        "code": 503,
                        "message": "Assistant unavailable; please retry.",
                    }
                )
            finally:
                logger.info(
                    json.dumps(
                        {
                            "event": "conversation",
                            "trace_id": trace_id,
                            "role": user.role,
                            "outcome": outcome,
                            "duration_ms": round((time.monotonic() - started) * 1000),
                        }
                    )
                )

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return app


def encode(event):
    return "data: " + json.dumps(event, default=str) + "\n\n"
