from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


# Test Configurations
@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Async HTTP test client using httpx ASGITransport."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
