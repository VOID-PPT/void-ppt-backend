"""Test bootstrap.

Environment must be configured BEFORE importing `src.main`, because settings
objects are instantiated at import time.

Priority: real environment variables (CI) > local `.env` > safe test fallbacks.
The fallbacks only exist so importing the app never crashes; DB-dependent tests
skip themselves when the resulting URL is unreachable.
"""

import os
from pathlib import Path

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
_has_env_file = _ENV_FILE.is_file()


def _env_value(key: str) -> str | None:
    """Read a key from the local .env without importing settings yet."""
    if not _has_env_file:
        return None
    for line in _ENV_FILE.read_text().splitlines():
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("AUTH_JWT_SECRET", "test-secret-not-for-production-32b")
os.environ.setdefault("AUTH_JWT_ALG", "HS256")

# Only fall back to an unreachable localhost URL when neither CI nor .env
# supplied one. Overriding a real URL here would silently skip DB tests.
if not os.environ.get("DATABASE_URL") and not _env_value("DATABASE_URL"):
    os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost:5432/test"

if not os.environ.get("AI_API_KEY") and not _env_value("AI_API_KEY"):
    os.environ["AI_API_KEY"] = ""

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
