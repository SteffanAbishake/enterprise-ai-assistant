import pytest

from app.config import Settings


@pytest.fixture
def settings():
    return Settings(
        _env_file=None,
        viewer_key="v" * 24,
        analyst_key="a" * 24,
        admin_key="z" * 24,
        app_mode="local",
        token_capacity=100,
    )
