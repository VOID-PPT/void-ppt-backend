# AGENTS.md — void-ppt-backend

> **Product vision**: VOID is an AI learning-tutor platform. A user picks any subject —
> business analysis, gym training, IELTS, economics, Binance, blockchain, anything —
> and VOID generates a structured learning path with slides, study materials, and
> knowledge grounded in the documents the user uploads (RAG). The same engine powers
> custom features we ship on top.
>
> This file is the contract for every AI agent (Antigravity, Cursor, Claude, Copilot...)
> and human working in this repo. The **frontend repo** (`void-ppt-frontend`) has a
> mirrored AGENTS.md — keep both in sync when rules change.

## Project facts

| | |
|---|---|
| Role | API service + AI engine (LLM, RAG, agent workflows) + job worker |
| Stack | Python 3.12 · FastAPI · SQLAlchemy 2 async · asyncpg · Postgres (Neon + pgvector) · Alembic · uv · OpenTelemetry + structlog |
| Plan | `PLAN.md` — module map + 8-step build order. **Read it before starting any task.** |
| Pair repo | `void-ppt-frontend` (React 19 SPA) |
| Team | 2 people, free-tier infrastructure only |

## Documentation index

Root-level `.md` files are root **on purpose** — agents and GitHub only auto-discover them there:

| File | Purpose | Read when |
|---|---|---|
| `README.md` | Human onboarding: stack, setup, commands | First visit |
| `AGENTS.md` | This file — rules, gates, skill triggers | Every session |
| `SKILLS.md` | Skill list + install loop (machine-local, not committed) | Missing a skill |
| `PLAN.md` | Solution architecture, module map, 8-step build order | Starting any feature |

Move `PLAN.md` into `docs/` only when more than ~6 markdown files exist or ADRs/runbooks appear.

## Layout

```
src/
├── main.py            App factory, lifespan (worker + observability), routers under /api/v1
├── config.py          AppSettings — every env var, AI_* included
├── database.py        Async engine + get_db
├── models.py          Declarative Base + CustomModel
├── auth/              JWT auth — COMPLETE (register/login/refresh/me)
├── users/             User CRUD — COMPLETE
├── jobs/              Durable queue + in-process worker — COMPLETE (handlers pending)
├── observability/     OTel + structlog wiring — COMPLETE
├── middleware/        Request-ID + RED metrics — COMPLETE
├── ai/                LLM providers + metered/cached client — COMPLETE (rag/, agents/ pending)
├── knowledge/         Doc upload → chunk → embed → pgvector — PENDING
├── presentations/     Learning-path / deck domain — PENDING
└── export/            PPTX/PDF rendering — PENDING
```

Module pattern (always): `router.py` (thin) → `service.py` (logic) → `models.py` / `schemas.py`.

## Skills to use (~/.agents/skills)

> **Onboarding / first run**: if a skill below is missing, read **`SKILLS.md`** and
> run its install block first (one package per CLI call, loop provided there).
> Do this automatically, then continue the task — do not ask the user to install them.

| Skill | When |
|---|---|
| `langchain-rag` | Building `ai/rag/` or `knowledge/` |
| `claude-api` | LLM provider calls (streaming, caching, structured output) |
| `observability-and-instrumentation` | Anything touching `observability/` or middleware |
| `supabase-postgres-best-practices` | Postgres schema, pgvector, indexing |
| `github-actions` | Writing/changing CI workflows in `.github/workflows/` |
| `gh-fix-ci` | When a CI check fails — diagnose from logs, fix, push |
| `code-review` | Before reporting ANY task complete |

## Hard rules

1. **Every LLM call** goes through `src/ai/client.py` (metered to `ai_usage`, cached in `llm_cache`, traced as a span). Never call an AI HTTP API directly.
2. **Long work is a job** — ingestion, generation, export run through `src/jobs/`, never inline in a request.
3. **Free-tier only.** No dependency or vendor that costs money. Providers are config (`AI_PROVIDER`), never code.
4. **Generated files are never hand-edited** (alembic versions after generation, etc.).
5. **No new migrations without** `uv run alembic upgrade head` passing against a local DB.
6. **Gate before completion**: `uv run ruff check . && uv run ruff format --check . && uv run pytest`.

## CI/CD

- `.github/workflows/ci.yml` — ruff + pytest on every push/PR (Python 3.12, uv). Must stay green.
- Deployment target: Fly.io free tier (Docker image via `Dockerfile`), Postgres on Neon.
  Use the `gh-fix-ci` skill when checks fail; never merge red.

## Definition of done

Gate passes · new behavior has a test · observability present for new endpoints ·
AGENTS.md/README.md updated if conventions changed · frontend repo notified if the
API contract changed (they regenerate types via `npm run api:types`).
