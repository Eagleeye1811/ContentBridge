from __future__ import annotations

import asyncio
import logging

from google import genai
from google.genai import types

from app.config import settings
from app.services.llm.base import LLMError, LLMNotConfigured, T

log = logging.getLogger(__name__)

# Google returns these when a model is busy (503/429) or retired for new keys
# (404), and an empty reply is an occasional glitch. All are worth a short
# retry and then a fallback model; anything else (a bad key, a malformed
# request) is not.
TRANSIENT = ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "no parsable content")
RETIRED = ("404", "NOT_FOUND")
# A used-up daily allowance (free tier) will not recover by waiting a few
# seconds, so move straight on to the next model.
DAILY_QUOTA = ("PerDay",)
RETRY_DELAYS = (2.0, 5.0)


class GeminiProvider:
    name = "gemini"

    def __init__(self) -> None:
        if not settings.gemini_api_key:
            raise LLMNotConfigured("GEMINI_API_KEY is not set")
        self._client = genai.Client(api_key=settings.gemini_api_key)

    async def complete_structured(
        self, *, system: str, prompt: str, schema: type[T], temperature: float | None = None
    ) -> T:
        models = [settings.llm_model]
        for name in settings.llm_fallback_model.split(","):
            if name.strip() and name.strip() not in models:
                models.append(name.strip())

        last_error: Exception | None = None
        for model in models:
            for attempt, delay in enumerate((0.0, *RETRY_DELAYS)):
                if delay:
                    await asyncio.sleep(delay)
                try:
                    return await self._call(model, system, prompt, schema, temperature)
                except Exception as exc:  # noqa: BLE001 - classified below
                    last_error = exc
                    text = str(exc)
                    if any(code in text for code in RETIRED):
                        log.warning("Gemini model %s unavailable; trying fallback", model)
                        break  # retrying a retired model is pointless
                    if any(code in text for code in DAILY_QUOTA):
                        log.warning("Gemini model %s daily quota used; trying fallback", model)
                        break
                    if not any(code in text for code in TRANSIENT):
                        raise LLMError(f"Gemini request failed: {exc}") from exc
                    log.warning("Gemini model %s busy (attempt %d)", model, attempt + 1)
        if last_error is not None and "PerDay" in str(last_error):
            raise LLMError(
                "Today's free AI allowance is used up on every model. Try again tomorrow, "
                "or enable billing on the Google AI Studio key."
            ) from last_error
        raise LLMError(
            f"The AI service is busy right now. Please try again in a minute. ({last_error})"
        ) from last_error

    async def _call(
        self, model: str, system: str, prompt: str, schema: type[T], temperature: float | None
    ) -> T:
        response = await self._client.aio.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system,
                temperature=settings.llm_temperature if temperature is None else temperature,
                response_mime_type="application/json",
                response_schema=schema,
            ),
        )

        parsed = response.parsed
        if isinstance(parsed, schema):
            return parsed
        # Fall back to the raw JSON when the SDK hands back a dict.
        if response.text:
            return schema.model_validate_json(response.text)
        raise LLMError("Gemini returned no parsable content")
