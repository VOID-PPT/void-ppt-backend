"""Job service: enqueue, claim, complete, fail, pause/resume for checkpoints."""

import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.jobs.models import Job

logger = structlog.get_logger(__name__)

JobHandler = Callable[[AsyncSession, Job], Awaitable[dict[str, Any] | None]]


async def enqueue(
    session: AsyncSession,
    job_type: str,
    payload: dict[str, Any],
    run_after: datetime | None = None,
) -> Job:
    job = Job(job_type=job_type, payload=payload, run_after=run_after or datetime.now(UTC))
    session.add(job)
    await session.flush()
    logger.info("job_enqueued", job_id=str(job.id), job_type=job_type)
    return job


async def claim_next(session: AsyncSession) -> Job | None:
    """Atomically claim one runnable job (FOR UPDATE SKIP LOCKED)."""
    now = datetime.now(UTC)
    job_ids = (
        (
            await session.execute(
                select(Job.id)
                .where(Job.status == "pending", Job.run_after <= now)
                .order_by(Job.run_after)
                .limit(1)
                .with_for_update(skip_locked=True)
            )
        )
        .scalars()
        .all()
    )
    if not job_ids:
        return None
    job_id = job_ids[0]
    await session.execute(
        update(Job)
        .where(Job.id == job_id)
        .values(status="running", attempts=Job.attempts + 1)
        .execution_options(synchronize_session=False)
    )
    await session.commit()
    # `expire_on_commit=False` + synchronize_session=False leave any cached
    # instance stale, so reload explicitly to return the claimed state.
    job = await session.get(Job, job_id, populate_existing=True)
    if job is not None:
        await session.refresh(job)
    return job


async def complete(session: AsyncSession, job: Job, result: dict[str, Any] | None) -> None:
    job.status = "done"
    job.result = result
    job.finished_at = datetime.now(UTC)
    await session.commit()


async def fail(
    session: AsyncSession, job: Job, error: str, retry_delay: timedelta = timedelta(seconds=30)
) -> None:
    if job.attempts < job.max_attempts:
        job.status = "pending"
        job.run_after = datetime.now(UTC) + retry_delay
    else:
        job.status = "failed"
        job.finished_at = datetime.now(UTC)
    job.error = error[:2000]
    await session.commit()
    logger.warning(
        "job_failed",
        job_id=str(job.id),
        job_type=job.job_type,
        attempts=job.attempts,
        retry=job.status == "pending",
        error=error,
    )


async def pause_for_input(session: AsyncSession, job: Job) -> None:
    """Human-in-the-loop checkpoint: pause until explicitly resumed."""
    job.status = "awaiting_input"
    await session.commit()


async def resume(session: AsyncSession, job_id: uuid.UUID, payload_patch: dict[str, Any]) -> Job:
    """Resume a paused job with (optional) user input merged into the payload."""
    job = await session.get(Job, job_id)
    if job is None or job.status != "awaiting_input":
        raise ValueError(f"Job {job_id} not resumable")
    job.payload = {**job.payload, **payload_patch}
    job.status = "pending"
    job.run_after = datetime.now(UTC)
    await session.commit()
    return job


async def get_job(session: AsyncSession, job_id: uuid.UUID) -> Job | None:
    return await session.get(Job, job_id)


async def pending_count(session: AsyncSession) -> int:
    return (
        await session.execute(select(func.count()).select_from(Job).where(Job.status == "pending"))
    ).scalar_one()
