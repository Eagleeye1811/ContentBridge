from __future__ import annotations

from google import genai
from google.genai import types

from app.config import settings
from app.services.llm.base import LLMError, LLMNotConfigured, T


class GeminiProvider:
    name = "gemini"

    def __init__(self) -> None:
        if not settings.gemini_api_key:
            raise LLMNotConfigured("GEMINI_API_KEY is not set")
        self._client = genai.Client(api_key=settings.gemini_api_key)

    async def complete_structured(
        self, *, system: str, prompt: str, schema: type[T], temperature: float | None = None
    ) -> T:
        try:
            response = await self._client.aio.models.generate_content(
                model=settings.llm_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    temperature=settings.llm_temperature if temperature is None else temperature,
                    response_mime_type="application/json",
                    response_schema=schema,
                ),
            )
        except Exception as exc:  # noqa: BLE001 - normalized for callers
            raise LLMError(f"Gemini request failed: {exc}") from exc

        parsed = response.parsed
        if isinstance(parsed, schema):
            return parsed
        # Fall back to the raw JSON when the SDK hands back a dict.
        if response.text:
            return schema.model_validate_json(response.text)
        raise LLMError("Gemini returned no parsable content")
