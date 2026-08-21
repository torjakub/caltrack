from functools import lru_cache

from app.core.config import settings
from app.llm.base import LLMProvider
from app.llm.none import NoneProvider

PROVIDERS: dict[str, type[LLMProvider]] = {"none": NoneProvider}


def _register_providers() -> None:
    """Imports are deferred so a missing optional dependency in one
    provider module can never break the others (or the `none` default)."""
    from app.llm.anthropic import AnthropicProvider
    from app.llm.cohere import CohereProvider
    from app.llm.ollama import OllamaProvider
    from app.llm.openai import OpenAIProvider

    PROVIDERS["anthropic"] = AnthropicProvider
    PROVIDERS["cohere"] = CohereProvider
    PROVIDERS["ollama"] = OllamaProvider
    PROVIDERS["openai"] = OpenAIProvider


_register_providers()


@lru_cache
def get_llm_provider() -> LLMProvider:
    provider_cls = PROVIDERS.get(settings.llm_provider, NoneProvider)
    return provider_cls()
