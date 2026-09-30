"""Embeddings. The local backend keeps retrieval working with no network."""

from __future__ import annotations

from collections.abc import Sequence
from functools import lru_cache
from typing import Protocol

import anyio

from app.config import settings


class Embedder(Protocol):
    dim: int
    name: str

    async def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


class FastEmbedEmbedder:
    """ONNX models running in-process. No API key, no egress."""

    def __init__(self, model_name: str, dim: int) -> None:
        from fastembed import TextEmbedding

        self.name = model_name
        self.dim = dim
        self._model = TextEmbedding(model_name=model_name)

    def _embed_sync(self, texts: Sequence[str]) -> list[list[float]]:
        return [vec.tolist() for vec in self._model.embed(list(texts))]

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        # ONNX inference is CPU-bound; keep it off the event loop.
        return await anyio.to_thread.run_sync(self._embed_sync, texts)


@lru_cache
def get_embedder() -> Embedder:
    if settings.embedding_provider == "local_fastembed":
        return FastEmbedEmbedder(settings.embedding_model, settings.embedding_dim)
    raise NotImplementedError(
        f"Embedding provider {settings.embedding_provider!r} is not implemented yet"
    )
