"""The ONLY entry point for LLM calls: metered, cached, traced.

Wraps any provider. Hard rule (AGENTS.md): feature code never calls a
provider directly; it calls ai.client.complete()/embed().
"""

import hashlib
import json
import time
import uuid
from typing import Any

import structlog
from opentelemetry import trace
from sqlalchemy import delete, select

from src.ai.models import AiUsage, LlmCache
from src.ai.providers import get_provider
from src.ai.types import LlmRequest, LlmResponse
from src.config import settings
from src.database import async_session_maker
from src.observability.setup import meter

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer(__name__)

ai_tokens_total = meter.create_counter(
    name="ai_tokens_total",
    description="LLM tokens by provider/model/direction",
)
ai_request_seconds = meter.create_histogram(
    name="ai_request_seconds",
    unit="s",
    description="LLM request latency",
)

CACHE_TTL_SECONDS = 24 * 60 * 60
_CACHE_MAX_ROWS = 1000


def _hash(parts: Any) -> str:
    return hashlib.sha256(json.dumps(parts, sort_keys=True).encode()).hexdigest()


async def complete(req: LlmRequest) -> LlmResponse:
    provider = get_provider()
    model = req.model or provider.default_model
    prompt_hash = _hash([req.system, req.prompt])
    params_hash = _hash([model, req.temperature, req.max_tokens, req.response_json])

    # 1. Cache lookup
    cached = await _cache_get(prompt_hash, model, params_hash)
    if cached is not None:
        ai_tokens_total.add(0, {"provider": provider.name, "model": model, "direction": "cached"})
        return cached

    # 2. Live call, traced
    start = time.perf_counter()
    with tracer.start_as_current_span(
        "ai.complete",
        attributes={
            "gen_ai.operation.name": "complete",
            "gen_ai.provider.name": provider.name,
            "gen_ai.request.model": model,
            "gen_ai.request.temperature": req.temperature,
            "gen_ai.request.max_tokens": req.max_tokens,
        },
    ) as span:
        try:
            response = await provider.complete(req)
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(trace.StatusCode.ERROR)
            raise
        latency = time.perf_counter() - start
        span.set_attribute("gen_ai.usage.input_tokens", response.prompt_tokens)
        span.set_attribute("gen_ai.usage.output_tokens", response.completion_tokens)
        span.set_attribute("gen_ai.response.latency_s", latency)

    # 3. Meter (ai_usage row) + metrics
    await _record_usage(req, response, latency, cache_hit=False)
    ai_tokens_total.add(
        response.prompt_tokens,
        {"provider": response.provider, "model": model, "direction": "input"},
    )
    ai_tokens_total.add(
        response.completion_tokens,
        {"provider": response.provider, "model": model, "direction": "output"},
    )
    ai_request_seconds.record(latency, {"provider": response.provider, "model": model})

    # 4. Store in cache
    await _cache_put(prompt_hash, model, params_hash, response)
    return response


async def embed(texts: list[str], user_id: uuid.UUID | None = None) -> list[list[float]]:
    provider = get_provider()
    if not hasattr(provider, "embed"):
        msg = f"Provider {provider.name} does not support embeddings"
        raise ValueError(msg)
    with tracer.start_as_current_span(
        "ai.embed",
        attributes={
            "gen_ai.operation.name": "embed",
            "gen_ai.provider.name": provider.name,
            "gen_ai.request.model": settings.AI_EMBEDDING_MODEL,
            "gen_ai.request.batch_size": len(texts),
        },
    ):
        vectors = await provider.embed(texts)  # type: ignore[attr-defined]
    start = time.perf_counter()
    await _record_usage(
        LlmRequest(prompt="", user_id=str(user_id) if user_id else None),
        LlmResponse(
            text="",
            model=settings.AI_EMBEDDING_MODEL,
            provider=provider.name,
            prompt_tokens=sum(len(t) // 4 for t in texts),
            completion_tokens=0,
            cost_usd=0.0,
            latency_seconds=0.0,
        ),
        time.perf_counter() - start,
        cache_hit=False,
        operation="embed",
    )
    return vectors


async def _cache_get(prompt_hash: str, model: str, params_hash: str) -> LlmResponse | None:
    async with async_session_maker() as session:
        row = (
            await session.execute(
                select(LlmCache)
                .where(
                    LlmCache.prompt_hash == prompt_hash,
                    LlmCache.model == model,
                    LlmCache.params_hash == params_hash,
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        if row is None:
            return None
        data = row.response
        return LlmResponse(
            text=data["text"],
            model=row.model,
            provider=data["provider"],
            prompt_tokens=row.prompt_tokens,
            completion_tokens=row.completion_tokens,
            cost_usd=data.get("cost_usd", 0.0),
            latency_seconds=0.0,
            cached=True,
        )


async def _cache_put(prompt_hash: str, model: str, params_hash: str, response: LlmResponse) -> None:
    async with async_session_maker() as session:
        session.add(
            LlmCache(
                prompt_hash=prompt_hash,
                model=model,
                params_hash=params_hash,
                response={
                    "text": response.text,
                    "provider": response.provider,
                    "cost_usd": response.cost_usd,
                },
                prompt_tokens=response.prompt_tokens,
                completion_tokens=response.completion_tokens,
            )
        )
        # crude LRU trim to bound table size at free-tier scale
        stale = (
            (
                await session.execute(
                    select(LlmCache.id).order_by(LlmCache.touched_at.desc()).offset(_CACHE_MAX_ROWS)
                )
            )
            .scalars()
            .all()
        )
        if stale:
            await session.execute(delete(LlmCache).where(LlmCache.id.in_(stale)))
        await session.commit()


async def _record_usage(
    req: LlmRequest,
    response: LlmResponse,
    latency: float,
    *,
    cache_hit: bool,
    operation: str = "complete",
) -> None:
    try:
        async with async_session_maker() as session:
            session.add(
                AiUsage(
                    user_id=uuid.UUID(req.user_id) if req.user_id else None,
                    provider=response.provider,
                    model=response.model,
                    operation=operation,
                    prompt_tokens=response.prompt_tokens,
                    completion_tokens=response.completion_tokens,
                    cost_usd=response.cost_usd,
                    cache_hit=cache_hit,
                    latency_seconds=latency,
                )
            )
            await session.commit()
    except Exception:
        # Metering must never break the feature call
        logger.exception("ai_usage_record_failed", model=response.model)
