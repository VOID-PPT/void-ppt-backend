from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware

from src.auth.router import router as auth_router
from src.config import settings
from src.database import engine
from src.exceptions import AppException, app_exception_handler
from src.users.router import router as users_router


# Application lifespan management (startup and shutdown)
@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Startup actions (e.g. database connect verification)
    yield
    # Shutdown actions: cleanly dispose database engine connection pool
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

# CORS middleware
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# Health check
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
