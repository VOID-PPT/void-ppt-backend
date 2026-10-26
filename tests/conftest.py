"""Test bootstrap.

Environment must be configured BEFORE importing `src.main`, because settings
objects are instantiated at import time. These values are test-only and never
used by a deployment.
"""

import os

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("AUTH_JWT_SECRET", "test-secret-not-for-production-32b")
os.environ.setdefault("AUTH_JWT_ALG", "HS256")
os.environ.setdefault("AI_API_KEY", "")

from collections.abc import AsyncIterator  # noqa: E402

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from src.main import app  # noqa: E402


# Test Configurations
@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Async HTTP test client using httpx ASGITransport."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
