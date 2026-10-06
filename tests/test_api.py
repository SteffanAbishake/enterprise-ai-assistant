import json
from uuid import uuid4

import httpx

from app.main import create_app


def events(response):
    return [
        json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")
    ]


async def test_full_chat_and_memory(settings):
    app = create_app(settings)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        session = str(uuid4())
        response = await client.post(
            "/chat",
            headers={"X-API-Key": "a" * 24},
            json={
                "session_id": session,
                "message": "Summarize all payment outages and recurring root causes",
            },
        )
        result = events(response)
        assert response.status_code == 200
        assert any(e.get("node") == "research" and e.get("depth") == 1 for e in result)
        answer = next(e for e in result if e["type"] == "answer")
        assert answer["citations"]
        assert "HR-001" not in response.text
        followup = await client.post(
            "/chat",
            headers={"X-API-Key": "a" * 24},
            json={"session_id": session, "message": "What about those retries?"},
        )
        assert events(followup)[0]["turns"] == 2
    await app.state.providers.close()


async def test_auth_filters_and_validation(settings):
    app = create_app(settings)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        body = {"session_id": str(uuid4()), "message": "payment"}
        assert (await client.post("/chat", json=body)).status_code == 401
        assert (
            await client.post(
                "/chat", headers={"X-API-Key": "v" * 24}, json={**body, "department": "hr"}
            )
        ).status_code == 403
        denied = await client.post(
            "/chat", headers={"X-API-Key": "v" * 24}, json={**body, "message": "analyze payments"}
        )
        assert any(e.get("code") == 403 for e in events(denied))
        invalid = await client.post(
            "/chat", headers={"X-API-Key": "v" * 24}, json={**body, "message": "x" * 2001}
        )
        assert invalid.status_code == 422
    await app.state.providers.close()


async def test_date_filter_no_evidence(settings):
    app = create_app(settings)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/chat",
            headers={"X-API-Key": "v" * 24},
            json={"session_id": str(uuid4()), "message": "payments", "since": "2030-01-01"},
        )
        answer = next(e for e in events(response) if e["type"] == "answer")
        assert not answer["citations"]
    await app.state.providers.close()


async def test_unrelated_question_after_payment_discussion(settings):
    app = create_app(settings)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        session = str(uuid4())
        headers = {"X-API-Key": "a" * 24}
        first = await client.post(
            "/chat",
            headers=headers,
            json={
                "session_id": session,
                "message": "What does the payment retry runbook recommend?",
            },
        )
        first_answer = next(e for e in events(first) if e["type"] == "answer")
        assert "RUN-001#0" in first_answer["citations"]
        for question in ["what is the usage of Docker?", "What is Kubernetes?", "What is the?"]:
            response = await client.post(
                "/chat", headers=headers, json={"session_id": session, "message": question}
            )
            answer = next(e for e in events(response) if e["type"] == "answer")
            assert answer["sources"] == []
            assert answer["citations"] == []
            assert "could not find sufficient authorized evidence" in answer["text"]
    await app.state.providers.close()
