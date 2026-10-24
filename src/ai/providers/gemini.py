"""Google Gemini provider (AI Studio API — free tier).

Uses the generateContent REST endpoint via the shared httpx client.
Costs stay at $0 within free-tier quotas; usage is still metered.
"""

import time
from typing import Any

import httpx
import structlog

from src.ai.types import LlmRequest, LlmResponse
from src.config import settings

logger = structlog.get_logger(__name__)

_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


class GeminiProvider:
    name = "gemini"
    default_model = settings.AI_MODEL

    def __init__(self) -> None:
        if not settings.AI_API_KEY:
            msg = "AI_API_KEY is required for the gemini provider (Google AI Studio key, free)"
            raise ValueError(msg)
        self._client = httpx.AsyncClient(
            base_url=_BASE_URL,
            timeout=settings.AI_TIMEOUT_SECONDS,
        )

    async def complete(self, req: LlmRequest) -> LlmResponse:
        model = req.model or self.default_model
        start = time.perf_counter()
        body = self._build_body(req)
        resp = await self._client.post(
            f"/models/{model}:generateContent",
            params={"key": settings.AI_API_KEY},
            json=body,
        )
        latency = time.perf_counter() - start
        resp.raise_for_status()
        data = resp.json()

        text = "".join(
            part.get("text", "")
            for part in data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        )
        usage = data.get("usageMetadata", {})
        return LlmResponse(
            text=text,
            model=model,
            provider=self.name,
            prompt_tokens=usage.get("promptTokenCount", 0),
            completion_tokens=usage.get("candidatesTokenCount", 0),
            cost_usd=0.0,  # free tier; metered for quotas, not billing
            latency_seconds=latency,
            raw=data,
        )

    def _build_body(self, req: LlmRequest) -> dict[str, Any]:
        body: dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": req.prompt}]}],
            "generationConfig": {
                "temperature": req.temperature,
                "maxOutputTokens": req.max_tokens,
            },
        }
        if req.system:
            body["systemInstruction"] = {"parts": [{"text": req.system}]}
        if req.response_json:
            body["generationConfig"]["responseMimeType"] = "application/json"
        return body

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Batched embeddings via text-embedding-004 (free tier)."""
        model = settings.AI_EMBEDDING_MODEL
        resp = await self._client.post(
            f"/models/{model}:batchEmbedContents",
            params={"key": settings.AI_API_KEY},
            json={
                "requests": [
                    {
                        "model": f"models/{model}",
                        "content": {"parts": [{"text": t}]},
                    }
                    for t in texts
                ]
            },
        )
        resp.raise_for_status()
        return [item["values"] for item in resp.json().get("embeddings", [])]

    async def aclose(self) -> None:
        await self._client.aclose()
