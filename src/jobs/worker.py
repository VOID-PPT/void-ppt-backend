"""In-process asyncio job worker.

Started from the app lifespan; polls the jobs table and executes registered
handlers. Single-writer claim via FOR UPDATE SKIP LOCKED means multiple
processes could run safely, but one worker suffices for a 2-person team's
free-tier deployment.
"""

import asyncio
from collections.abc import Callable

import structlog
from opentelemetry import trace
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database import async_session_maker
from src.jobs import service as job_service
from src.jobs.models import Job
from src.jobs.service import JobHandler
from src.observability.setup import meter

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer(__name__)

job_duration = meter.create_histogram(
    name="job_duration_seconds",
    unit="s",
    description="Job execution duration by type and status",
)
jobs_pending_gauge = meter.create_observable_gauge(
    name="jobs_pending",
    description="Jobs waiting to run",
)


class JobRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, JobHandler] = {}

    def register(self, job_type: str) -> Callable[[JobHandler], JobHandler]:
        def decorator(fn: JobHandler) -> JobHandler:
            if job_type in self._handlers:
                msg = f"Duplicate job handler: {job_type}"
                raise ValueError(msg)
            self._handlers[job_type] = fn
            return fn

        return decorator

    def get(self, job_type: str) -> JobHandler | None:
        return self._handlers.get(job_type)

    @property
    def types(self) -> list[str]:
        return sorted(self._handlers)


registry = JobRegistry()


class JobWorker:
    def __init__(self, poll_interval: float = 2.0, batch_size: int = 1) -> None:
        self.poll_interval = poll_interval
        self.batch_size = batch_size
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()
        self._pending_callback = lambda: 0  # replaced by metric wiring

    def start(self) -> None:
        self._task = asyncio.create_task(self._run(), name="job-worker")
        logger.info("job_worker_started", handlers=registry.types)

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            await asyncio.wait([self._task], timeout=10)
        logger.info("job_worker_stopped")

    async def _run(self) -> None:
        consecutive_failures = 0
        while not self._stop.is_set():
            try:
                ran = await self._tick()
                if not ran:
                    consecutive_failures = 0
                    await asyncio.sleep(self.poll_interval)
                    continue
            except asyncio.CancelledError:
                break
            except Exception as exc:
                consecutive_failures += 1
                # Condensed log (no traceback spam) with exponential backoff
                backoff = min(60.0, self.poll_interval * 2 ** min(consecutive_failures, 5))
                logger.warning(
                    "job_worker_tick_failed",
                    error=f"{type(exc).__name__}: {exc}",
                    backoff_seconds=backoff,
                    consecutive_failures=consecutive_failures,
                )
                await asyncio.sleep(backoff)

    async def _tick(self) -> bool:
        ran_any = False
        for _ in range(self.batch_size):
            async with async_session_maker() as session:
                job = await job_service.claim_next(session)
                if job is None:
                    break
                ran_any = True
                await self._execute(session, job)
        return ran_any

    async def _execute(self, session: AsyncSession, job: Job) -> None:
        handler = registry.get(job.job_type)
        with tracer.start_as_current_span(
            "job.execute", attributes={"job.type": job.job_type, "job.id": str(job.id)}
        ) as span:
            if handler is None:
                await job_service.fail(session, job, f"No handler for {job.job_type}")
                span.set_status(trace.StatusCode.ERROR)
                return
            try:
                result = await handler(session, job)
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(trace.StatusCode.ERROR)
                await job_service.fail(session, job, repr(exc))
                job_duration.record(
                    0, {"job.type": job.job_type, "job.status": "failed"}
                )  # duration unknown; count only
                return
            if job.status == "awaiting_input":
                span.set_attribute("job.awaiting_input", True)
                job_duration.record(0, {"job.type": job.job_type, "job.status": "awaiting_input"})
                return
            await job_service.complete(session, job, result)
            job_duration.record(0, {"job.type": job.job_type, "job.status": "done"})
            logger.info("job_done", job_id=str(job.id), job_type=job.job_type)


worker = JobWorker()


def start_worker() -> None:
    if settings.ENVIRONMENT == "test":
        return
    worker.start()
