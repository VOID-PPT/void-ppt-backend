# void-ptt-backend

**VOID** is an AI learning-tutor platform: a user picks any subject — business analysis,
gym, IELTS, economics, Binance, blockchain, anything — and VOID builds a structured
learning path with slides and study materials grounded in the user's own uploaded
documents (RAG).

This repo is the API service and AI engine: FastAPI + LLM providers + RAG pipeline +
agent workflows + background job worker. The client lives in
[`void-ppt-frontend`](../void-ppt-frontend) (mirrored README/AGENTS.md — keep in sync).

## Stack

Python 3.12 · FastAPI · SQLAlchemy 2 (async) · asyncpg · PostgreSQL (Neon + pgvector) ·
Alembic · Pydantic v2 · uv · OpenTelemetry + structlog

## Status

| Module | State |
|---|---|
| `auth/`, `users/` | ✅ complete |
| `observability/`, `middleware/` (OTel, RED metrics, request-ID, health probes) | ✅ complete |
| `jobs/` (durable Postgres queue + in-process worker, human-checkpoint support) | ✅ complete |
| `ai/` (provider abstraction, Gemini free tier, metered + cached client) | ✅ complete |
| `knowledge/` (ingest → chunk → embed → hybrid retrieval) | 🚧 next (PLAN.md step 4) |
| `presentations/`, `ai/agents/`, `export/` | 🚧 planned |

Full architecture and build order: **[PLAN.md](PLAN.md)** · Working agreement: **[AGENTS.md](AGENTS.md)** ·
Agent skills (machine-local, install once): **[SKILLS.md](SKILLS.md)**

## Getting started

Requires [uv](https://docs.astral.sh/uv/) and Postgres (local, Supabase, or Neon).

```bash
uv sync --all-groups
cp .env.example .env       # DATABASE_URL, AUTH_JWT_SECRET, AI_API_KEY (free: aistudio.google.com/apikey)
make migrate               # alembic upgrade head
make dev                   # http://localhost:8000 — docs at /docs (local/staging)
```

Health probes: `/health/live` (process) · `/health/ready` (DB + pool + queue).

## Commands

| Command | Purpose |
|---|---|
| `make dev` | Run API with reload |
| `make test` | Async pytest suite |
| `make lint` / `make format` | Ruff check / format |
| `make migrate` / `make revision msg=...` | Alembic |

## Observability

OpenTelemetry traces/metrics/logs export via OTLP when `OTEL_EXPORTER_OTLP_ENDPOINT`
is set (Grafana Cloud free tier); otherwise no-op. Every LLM call is metered into
`ai_usage`, cached in `llm_cache`, and traced with `gen_ai.*` attributes. Structured
JSON logs with request-ID correlation.

## CI/CD

GitHub Actions (`.github/workflows/ci.yml`): ruff + format check + pytest on every
push/PR. Deploy: Docker image → Fly.io free tier; Postgres on Neon. Free-tier only —
see PLAN.md §1.

## Conventions

- Module pattern: `router.py` (thin) → `service.py` → `models.py`/`schemas.py`
- LLM calls only through `src/ai/client.py` — always metered, cached, traced
- Long work only through `src/jobs/` — never inline in a request
- Gate: `uv run ruff check . && uv run ruff format --check . && uv run pytest`
