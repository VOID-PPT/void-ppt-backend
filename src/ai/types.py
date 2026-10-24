"""Provider-agnostic LLM request/response types."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, kw_only=True)
class LlmRequest:
    prompt: str
    system: str | None = None
    model: str | None = None  # provider default when None
    temperature: float = 0.7
    max_tokens: int = 4096
    response_json: bool = False
    user_id: str | None = None  # for per-user budget attribution
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, kw_only=True)
class LlmResponse:
    text: str
    model: str
    provider: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    latency_seconds: float
    cached: bool = False
    raw: dict[str, Any] | None = None
