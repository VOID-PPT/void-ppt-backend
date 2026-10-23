# Multi-stage production build using uv (fast, minimal RAM, ultra lightweight)
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# Install production dependencies without dev tools
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# Copy application code
COPY . .

# Final sync including project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev


# Minimal final runtime image
FROM python:3.12-slim-bookworm AS runner

WORKDIR /app

# Run as non-root user for security
RUN useradd -u 1000 -m -s /bin/bash appuser

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Copy synced project and virtual environment from builder
COPY --from=builder --chown=appuser:appuser /app /app

USER appuser

EXPOSE 8000

# Run uvicorn with proxy headers enabled (for Caddy/Nginx)
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--proxy-headers"]
