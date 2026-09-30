"""Provider-agnostic LLM interface.

Every call site asks for *structured* output against a pydantic model, so the
rest of the system never parses free text out of an LLM response.
"""

from __future__ import annotations

from typing import Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMError(RuntimeError):
    pass


class LLMNotConfigured(LLMError):
    """Raised when the selected provider has no credentials."""


class LLMProvider(Protocol):
    name: str

    async def complete_structured(
        self,
        *,
        system: str,
        prompt: str,
        schema: type[T],
        temperature: float | None = None,
    ) -> T: ...
