"""LlmProvider protocol + provider registry.

Providers are configuration, never code: the active provider is chosen by
settings.AI_PROVIDER and instantiated here. All providers are free-tier.
"""

from typing import Protocol

from src.ai.types import LlmRequest, LlmResponse


class LlmProvider(Protocol):
    name: str
    default_model: str

    async def complete(self, req: LlmRequest) -> LlmResponse: ...


def get_provider() -> LlmProvider:
    from src.config import settings

    provider_name = settings.AI_PROVIDER.lower()
    if provider_name == "gemini":
        from src.ai.providers.gemini import GeminiProvider

        return GeminiProvider()
    if provider_name == "groq":
        from src.ai.providers.groq import GroqProvider

        return GroqProvider()
    if provider_name == "ollama":
        from src.ai.providers.ollama import OllamaProvider

        return OllamaProvider()
    msg = (
        f"Unknown AI_PROVIDER '{settings.AI_PROVIDER}'. "
        "Supported: gemini, groq, ollama (set AI_PROVIDER in .env)"
    )
    raise ValueError(msg)
