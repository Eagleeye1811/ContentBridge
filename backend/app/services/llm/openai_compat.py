from __future__ import annotations

from openai import AsyncOpenAI

from app.config import settings
from app.services.llm.base import LLMError, LLMNotConfigured, T


class OpenAICompatibleProvider:
    """Works against OpenAI, OpenRouter, vLLM, Ollama and friends."""

    name = "openai_compatible"

    def __init__(self) -> None:
        if not settings.openai_api_key:
            raise LLMNotConfigured("OPENAI_API_KEY is not set")
        self._client = AsyncOpenAI(
            api_key=settings.openai_api_key, base_url=settings.openai_base_url
        )

    async def complete_structured(
        self, *, system: str, prompt: str, schema: type[T], temperature: float | None = None
    ) -> T:
        try:
            completion = await self._client.chat.completions.parse(
                model=settings.llm_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                response_format=schema,
                temperature=settings.llm_temperature if temperature is None else temperature,
            )
        except Exception as exc:  # noqa: BLE001 - normalized for callers
            raise LLMError(f"OpenAI-compatible request failed: {exc}") from exc

        parsed = completion.choices[0].message.parsed
        if parsed is None:
            raise LLMError("Model returned no parsable content")
        return parsed
