# void-ptt-backend — Rebuild Plan

**Product**: VOID is an AI learning-tutor platform — a user picks any subject
(business analysis, gym, IELTS, economics, Binance, blockchain, ...) and VOID
generates a structured learning path with slides and study materials grounded
in the user's uploaded documents (RAG).

**Audience:** 2-person team. **Constraints:** free-tier hosting, minimal ops, no managed paid services.
**Mission:** the AI engine for VOID — learning paths generated/revised by LLM + RAG
with agent workflows, wrapped in a fast, observable FastAPI service.

> The existing `src/` (auth, users, database, pagination) is solid and stays as the foundation.
> Nothing gets deleted unless replaced in the same change. Rework is additive: new modules below.

## 0. Operating principles (read first)

1. **Boring is a feature.** One service, one Postgres, one queue table. No Redis, no Celery, no Kafka, no microservices.
2. **Free tier first.** Every infra choice must run at $0 for the first ~100 users. Paid upgrades are a config change, not a rewrite.
3. **Observe before you optimize.** Structured logs + traces + metrics from day one; profile only what the data says is slow.
4. **AI calls are the product AND the cost center.** Every LLM call is logged, cached, and bounded.

## 1. Free-tier deployment target

| Concern | Choice | Free tier | Why |
|---|---|---|---|
| API hosting | **Fly.io** (or Render free) | 3 shared VMs, 256MB | Docker already exists; Fly handles autosleep |
| Postgres | **Neon** | 0.5GB, autosuspend | Serverless PG, pgvector available |
| Vector store | **pgvector on Neon** | included | No separate vector DB to run |
| LLM | **Cloudflare Workers AI** / **Groq free tier** / **Google AI Studio (Gemini free)** | generous free quotas | No billing risk; swap via one config |
| Embeddings | Gemini `text-embedding` free tier | free | Store as pgvector |
| Frontend | **Cloudflare Pages** (already static dist) | unlimited | Pair with frontend repo |
| Observability | **Grafana Cloud free** (or Axiom/Better Stack free) | 50GB logs | OTLP export from app |
| Background jobs | **in-process asyncio queue + DB table** | $0 | Two people don't need Celery |

LLM provider abstraction: a single `src/ai/providers/` module with a `LlmProvider` protocol. Default: Gemini free tier (Google AI Studio key). Failover order configured, never hardcoded. Swap to Groq/CF/Ollama without touching feature code.

## 2. Target architecture (module map)

```
src/
├── main.py                  # existing app factory + middleware wiring
├── config.py                # existing settings (extend: AI_*, OTEL_*)
├── auth/                    # KEEP — JWT auth (existing)
├── users/                   # KEEP — user CRUD (existing)
├── database.py              # KEEP — async engine + pgvector ext migration
├── pagination.py            # KEEP
│
├── presentations/           # NEW — core domain (CRUD, versions, slides)
│   ├── models.py            #   Presentation, Slide, Asset + repositories
│   ├── schemas.py / router.py / service.py
│
├── ai/                      # NEW — the "built-in AI model" layer
│   ├── providers/           #   LlmProvider protocol + gemini/groq/cf/ollama impls
│   ├── embeddings.py        #   embed() with DB-level result cache
│   ├── rag/                 #   chunking, retrieval, reranking, prompt assembly
│   ├── agents/              #   workflow orchestration (see §4)
│   ├── prompts/             #   versioned prompt templates (files, not strings)
│   └── budget.py            #   per-user/per-day token/cost guard rails
│
├── knowledge/               # NEW — RAG ingestion
│   ├── models.py            #   KnowledgeDoc, Chunk (embedding vector column)
│   ├── ingest.py            #   extract → clean → chunk → embed → upsert pipeline
│   └── router.py            #   upload endpoints (PDF/DOCX/MD/txt)
│
├── jobs/                    # NEW — durable async work
│   ├── models.py            #   Job table: id, type, payload, status, attempts, run_after
│   ├── worker.py            #   asyncio loop, spawned in lifespan, sleeps when idle
│   └── handlers/            #   ingest_doc, generate_deck, export_pptx
│
├── observability/           # NEW — §3
├── middleware/              # request timing, request-id propagation
└── export/                  # PPTX/PDF rendering (python-pptx; pure-python)
```

## 3. Observability (do this before AI features)

**Stack: OpenTelemetry + structlog → Grafana Cloud free tier (OTLP endpoint).**

- `observability/setup.py` — init OTel tracer/meter/log exporters from settings (no-op if env vars unset, so local dev needs nothing)
- **Traces:** auto-instrument FastAPI + asyncpg + httpx. Every LLM call is a span with `gen_ai.*` attributes (prompt tokens, completion tokens, model, latency). One trace per request, child spans per agent step.
- **Metrics:** RED metrics per route (request rate/errors/duration), plus custom:
  - `ai_tokens_total{model, direction}` counter
  - `ai_request_seconds` histogram (p95 = LLM latency at a glance)
  - `rag_retrieval_score` histogram (quality signal)
  - `jobs_pending` gauge, `job_duration_seconds` histogram
  - DB pool gauges (`pool_size`, `checked_out`)
- **Logs:** structlog JSON to stdout; `request_id` from middleware bound into every log line; Fly.io/Render ship stdout for free; Grafana/Axiom ingest.
- **/health split:** `/health/live` (process up) and `/health/ready` (DB ping + pool stat + queue depth) — Fly checks readiness before routing traffic.

Performance practices baked in:
- asyncpg prepared statements; SQLAlchemy 2.0 async with `pool_pre_ping`
- No N+1: repositories return fully-hydrated aggregates; load only what the route serializes
- Response compression + pagination already present; add `ETag` caching for GET presentations
- LLM responses cached in DB by (prompt_hash, model, params) — repeated generations cost $0

## 4. AI layer — LLM + RAG + agent workflows

### 4.1 Provider abstraction
```python
class LlmProvider(Protocol):
    async def complete(self, req: LlmRequest) -> LlmResponse: ...
    async def stream(self, req: LlmRequest) -> AsyncIterator[LlmChunk]: ...
    async def embed(self, texts: list[str]) -> list[list[float]]: ...
```
- `providers/gemini.py` (default, free), `providers/groq.py`, `providers/cloudflare.py`, `providers/ollama.py` (local dev)
- httpx.AsyncClient shared instance, connection-pooled, per-provider timeouts + retry with jitter
- Every call metered (tokens/cost) and traced, results cached

### 4.2 RAG pipeline (`ai/rag/`)
1. **Ingest** (`knowledge/ingest.py`): upload → pymupdf/docx extraction → normalize → chunk (semantic, ~512 tok, 15% overlap) → embed (batched) → store in pgvector
2. **Retrieve:** hybrid search = pgvector cosine ANN (`HNSW` index) + Postgres FTS (tsvector) → reciprocal-rank fusion → optional LLM rerank for top-k
3. **Generate:** prompt assembled from versioned templates + retrieved chunks (with citations back to source doc/page) → provider.complete
4. **Guard:** `ai/budget.py` — per-user daily token budget from settings; 429-style domain error when exceeded

### 4.3 Agent workflows (`ai/agents/`) — keep it *small*
No LangGraph/CrewAI dependency. A ~200-line deterministic orchestrator:

```python
class AgentStep:
    name: str
    run: Callable[[Ctx], Awaitable[StepResult]]


class Workflow:
    steps: list[AgentStep]
    # supports: linear, retry-per-step, human-in-the-loop checkpoints,
    # conditional branching, full trace emitted as OTel span tree
```

**Deck generation workflow** (the product's core loop):
```
INTAKE → OUTLINE → RESEARCH(rag retrieve, cite sources)
      → [CHECKPOINT: user approves/edits outline]
      → SLIDES (per-slide LLM, parallel, budget-checked)
      → ASSEMBLE → EXPORT (pptx) → DONE
```
- Every step is a job row → crash-safe resume from the last completed step
- Each step emits its own span; the whole workflow is one trace you can open in Grafana
- Human-in-the-loop = workflow pauses, job status `awaiting_input`, frontend polls

## 5. Data model additions (alembic migrations)

- `presentations`, `slides` (JSONB content, versioned), `assets`
- `knowledge_docs`, `chunks` (text + `embedding vector(n)` + tsvector + doc/page refs)
- `jobs` (durable queue)
- `llm_cache` (prompt_hash, model, response, tokens, created_at)
- `ai_usage` (user_id, model, prompt_tokens, completion_tokens, cost_usd, request_id) — the billing-telemetry table

## 6. API additions (all under /api/v1)

```
POST /presentations                 create + enqueue generate workflow
GET  /presentations                 paginated (exists pattern)
GET  /presentations/{id}            detail w/ slides
PATCH /presentations/{id}           rename etc.
POST /presentations/{id}/approve    outline checkpoint resume
POST /knowledge/documents           upload → enqueue ingest job
GET  /knowledge/documents           list + status
GET  /jobs/{id}                     poll job/workflow status
GET  /ai/usage                      own token usage (from ai_usage)
```

## 7. Build order (each step ships something usable)

1. **Observability + health split + middleware** (§3) — foundation, verifies free Grafana ingest
2. **jobs/** table + in-process worker — powers everything async
3. **ai/providers/** + `ai_usage` + `llm_cache` — metered LLM calls working end-to-end w/ Gemini free key
4. **presentations/** CRUD — domain models + routers (keep existing patterns)
5. **knowledge/ + rag/** — upload → chunk → embed → hybrid retrieval w/ citations
6. **ai/agents/** deck workflow + checkpoint resume — the product loop
7. **export/** PPTX rendering
8. Frontend consumes: session ✓ → then presentations + job polling

## 8. Agent skills for backend work (installed at ~/.agents/skills/)

- `langchain-rag` — RAG pipeline patterns (chunking, retrieval, reranking) when building `ai/rag/`
- `claude-api` — LLM call patterns: caching, streaming, tool use, structured output
- `observability-and-instrumentation` — when wiring OTel/metrics in step 1
- `supabase-postgres-best-practices` — pgvector + Postgres indexing/RLS patterns for `knowledge/`
- `code-review` — before merging anything

## 9. Non-goals (explicit)

- No Celery/Redis/RabbitMQ — DB queue suffices for 2 people
- No Kubernetes, no paid APM, no paid vector DB
- No multi-region, no horizontal scaling before user growth demands it
- No LangGraph/agent frameworks — the orchestrator is ours, ~200 LOC, fully traced
