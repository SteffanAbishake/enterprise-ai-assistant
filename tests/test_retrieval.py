from uuid import uuid4

from app.models import ChatRequest
from app.providers import Providers
from app.retrieval import Retrieval, fuse
from app.security import authenticate


async def test_acl_and_dense_failure(settings):
    provider = Providers(settings)
    retrieval = Retrieval(settings, provider)
    viewer = authenticate("v" * 24, settings)
    request = ChatRequest(session_id=uuid4(), message="payment")
    settings.app_mode = "live"

    async def fail(_):
        raise TimeoutError()

    provider.embed = fail
    rows, warnings = await retrieval.search(viewer, request, "payment")
    assert rows and warnings
    assert all(row["access_level"] == "internal" and row["department"] != "hr" for row in rows)
    await provider.close()


def test_rrf_boosts_shared_result():
    result = fuse([{"id": "a"}, {"id": "b"}], [{"id": "b"}, {"id": "c"}], 3)
    assert result[0]["id"] == "b"
