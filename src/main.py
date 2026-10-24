from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from src.auth.router import router as auth_router
from src.config import settings
from src.database import engine
from src.exceptions import AppException, app_exception_handler
from src.jobs.router import router as jobs_router
from src.jobs.worker import start_worker, worker
from src.middleware.request_context import RequestContextMiddleware
from src.observability.setup import setup_observability
from src.users.router import router as users_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    setup_observability(None)
    start_worker()
    yield
    # Shutdown actions: stop worker, dispose DB pool
    await worker.stop()
    await engine.dispose()


app_kwargs: dict[str, Any] = {
    "title": settings.APP_NAME,
    "version": settings.APP_VERSION,
    "lifespan": lifespan,
}

# Disable interactive docs in production environments
SHOW_DOCS_IN = {"local", "staging"}
if settings.ENVIRONMENT not in SHOW_DOCS_IN:
    app_kwargs["openapi_url"] = None
    app_kwargs["docs_url"] = None
    app_kwargs["redoc_url"] = None

app = FastAPI(**app_kwargs)

# Exception handlers
app.add_exception_handler(AppException, app_exception_handler)

# Middleware (outermost last)
app.add_middleware(RequestContextMiddleware)

# CORS middleware
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# Health checks — split for deployment probes (Fly.io readiness vs liveness)
@app.get(
    "/health/live",
    status_code=status.HTTP_200_OK,
    tags=["health"],
    summary="Liveness probe — process is up",
)
async def health_live() -> dict[str, str]:
    return {"status": "ok", "app": settings.APP_NAME, "env": settings.ENVIRONMENT}


@app.get(
    "/health/ready",
    status_code=status.HTTP_200_OK,
    tags=["health"],
    summary="Readiness probe — DB reachable, pool + queue stats",
)
async def health_ready() -> dict[str, Any]:
    db_ok = True
    pool_stat: dict[str, int] = {}
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        pool = engine.pool
        pool_stat = {
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
        }
    except Exception:
        db_ok = False

    return {
        "status": "ok" if db_ok else "degraded",
        "db": db_ok,
        "pool": pool_stat,
        "app": settings.APP_NAME,
        "env": settings.ENVIRONMENT,
    }


# Backwards-compatible health endpoint
@app.get(
    "/health",
    status_code=status.HTTP_200_OK,
    tags=["health"],
    summary="Health check endpoint",
)
async def health_check() -> dict[str, str]:
    return {"status": "ok", "app": settings.APP_NAME, "env": settings.ENVIRONMENT}


# API Routers under /api/v1
app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(jobs_router, prefix="/api/v1")
