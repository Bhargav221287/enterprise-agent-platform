"""LLM package exports and provider factory."""

import logging

from app.llm.base import LLMProvider
from app.llm.mock import MockLLM
from app.llm.openai import OpenAILLM

logger = logging.getLogger(__name__)


def get_llm_provider(
    provider_name: str = "mock",
    model: str = "mock-agent-v1",
    api_key: str = "",
    mock_latency: float = 0.001,
) -> LLMProvider:
    """Instantiate and return the configured LLM provider."""
    normalized = provider_name.lower().strip()
    if normalized == "mock":
        return MockLLM(latency_seconds=mock_latency)
    elif normalized in ("openai", "azure_openai"):
        return OpenAILLM(api_key=api_key, model=model)
    else:
        logger.warning("Unrecognized LLM provider '%s', defaulting to MockLLM", provider_name)
        return MockLLM(latency_seconds=mock_latency)


__all__ = ["LLMProvider", "MockLLM", "OpenAILLM", "get_llm_provider"]
