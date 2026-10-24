"""Job queue unit tests against the claim/resume state machine.

Requires a reachable Postgres (DATABASE_URL). Skips otherwise so the gate
stays green in environments without a database.
"""

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.jobs import service as job_service


async def _db_available() -> bool:
    from src.database import engine

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    if not await _db_available():
        pytest.skip("Postgres not reachable — set DATABASE_URL to run job tests")
    from src.database import async_session_maker

    async with async_session_maker() as s:
        yield s


@pytest.mark.asyncio
async def test_enqueue_and_claim(session: AsyncSession) -> None:
    job = await job_service.enqueue(session, "test.echo", {"n": 1})
    await session.commit()
    assert job.status == "pending"

    claimed = await job_service.claim_next(session)
    assert claimed is not None
    assert claimed.job_type == "test.echo"
    assert claimed.status == "running"
    assert claimed.attempts == 1


@pytest.mark.asyncio
async def test_claim_respects_run_after(session: AsyncSession) -> None:
    future = datetime.now(UTC) + timedelta(minutes=10)
    job = await job_service.enqueue(session, "test.scheduled", {"n": 1}, run_after=future)
    await session.commit()

    claimed = await job_service.claim_next(session)
    if claimed is not None and claimed.id == job.id:
        pytest.fail("future job was claimed early")
    # cleanup
    await session.delete(job)
    await session.commit()


@pytest.mark.asyncio
async def test_pause_and_resume(session: AsyncSession) -> None:
    job = await job_service.enqueue(session, "test.checkpoint", {})
    await session.commit()

    await job_service.pause_for_input(session, job)
    assert job.status == "awaiting_input"

    resumed = await job_service.resume(session, job.id, {"user_choice": "approved"})
    assert resumed.status == "pending"
    assert resumed.payload["user_choice"] == "approved"


@pytest.mark.asyncio
async def test_fail_exhausts_attempts(session: AsyncSession) -> None:
    job = await job_service.enqueue(session, "test.failing", {})
    job.max_attempts = 1
    await session.commit()

    claimed = await job_service.claim_next(session)
    assert claimed is not None
    await job_service.fail(session, claimed, "boom")
    assert claimed.status == "failed"
    assert claimed.error == "boom"


@pytest.mark.asyncio
async def test_get_job_not_found(session: AsyncSession) -> None:
    assert await job_service.get_job(session, uuid.uuid4()) is None
