"""Provider selection. Swapping providers is an env change, not a code change."""

from __future__ import annotations

from functools import lru_cache

from app.config import settings
from app.services.llm.base import LLMError, LLMNotConfigured, LLMProvider
from app.services.llm.stub import StubProvider


import logging

log = logging.getLogger(__name__)


@lru_cache
def get_llm() -> LLMProvider:
    provider = settings.llm_provider
    if provider == "stub":
        return StubProvider()
    if provider == "gemini":
        from app.services.llm.gemini import GeminiProvider

        try:
            return GeminiProvider()
        except LLMNotConfigured:
            log.warning("GEMINI_API_KEY is not set; falling back to StubProvider for offline execution.")
            return StubProvider()
    if provider == "openai_compatible":
        from app.services.llm.openai_compat import OpenAICompatibleProvider

        try:
            return OpenAICompatibleProvider()
        except LLMNotConfigured:
            log.warning("OPENAI_API_KEY is not set; falling back to StubProvider for offline execution.")
            return StubProvider()
    raise LLMError(f"Unknown LLM provider: {provider!r}")


def llm_available() -> bool:
    """True when extraction can run. Lets the pipeline degrade gracefully."""
    try:
        get_llm()
        return True
    except LLMError:
        return False


__all__ = ["LLMError", "LLMNotConfigured", "LLMProvider", "get_llm", "llm_available"]

