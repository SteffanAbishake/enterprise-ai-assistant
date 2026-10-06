import json
from pathlib import Path
from uuid import uuid4

import httpx
from streamlit.testing.v1 import AppTest

from app.main import create_app
from app.security import authenticate
from app.tools import enterprise_lookup


async def test_real_local_mcp(settings):
    user = authenticate("a" * 24, settings)
    result = await enterprise_lookup(user, 15)
    assert result["owner"] == "Payments Operations"


def test_streamlit_starts():
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "frontend/chat.py").run(
        timeout=15
    )
    assert not app.exception
    assert app.title[0].value == "Demo Bank · Knowledge Assistant"


async def test_llm_failure_uses_evidence(settings):
    app = create_app(settings)
    settings.app_mode = "live"

    async def fail(*args):
        raise TimeoutError("injected failure")

    app.state.providers.embed = fail
    app.state.providers.complete = fail
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/chat",
            headers={"X-API-Key": "v" * 24},
            json={"session_id": str(uuid4()), "message": "payment retry runbook"},
        )
    frames = [json.loads(x[6:]) for x in response.text.splitlines() if x.startswith("data: ")]
    answer = next(x for x in frames if x["type"] == "answer")
    assert "Evidence excerpts" in answer["text"]
    assert any("Language model unavailable" in w for w in answer["warnings"])
    await app.state.providers.close()


async def test_mcp_failure_visible(settings, monkeypatch):
    settings.mcp_enabled = True

    async def fail(*args):
        raise TimeoutError()

    monkeypatch.setattr("app.graph.enterprise_lookup", fail)
    app = create_app(settings)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/chat",
            headers={"X-API-Key": "a" * 24},
            json={"session_id": str(uuid4()), "message": "who owns payments"},
        )
    assert "Service catalog unavailable" in response.text
    await app.state.providers.close()
