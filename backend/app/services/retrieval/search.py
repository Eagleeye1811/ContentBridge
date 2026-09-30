"""Retrieval always returns provenance. There is no code path that hands a
chunk to an LLM without the blocks it came from."""

from __future__ import annotations

import uuid

from app.services.indexing.embeddings import get_embedder
from app.services.indexing.qdrant_store import SearchHit, VectorStore


async def search(document_id: uuid.UUID, query: str, limit: int = 8) -> list[SearchHit]:
    embedder = get_embedder()
    vectors = await embedder.embed([query])
    if not vectors:
        return []
    store = VectorStore()
    try:
        return await store.search(vectors[0], document_id, limit=limit)
    finally:
        await store.close()
