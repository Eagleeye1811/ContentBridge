"""Qdrant access. Payloads carry provenance so a hit is citable on its own."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from qdrant_client import AsyncQdrantClient, models

from app.config import settings


@dataclass(slots=True)
class ChunkPoint:
    point_id: str
    vector: list[float]
    document_id: uuid.UUID
    block_ids: list[uuid.UUID]
    text: str
    page_no: int
    section_path: str


@dataclass(slots=True)
class SearchHit:
    text: str
    block_ids: list[uuid.UUID]
    page_no: int
    section_path: str
    score: float


class VectorStore:
    def __init__(self, url: str | None = None, collection: str | None = None) -> None:
        self._client = AsyncQdrantClient(url=url or settings.qdrant_url)
        self.collection = collection or settings.qdrant_collection

    async def ensure_collection(self, dim: int) -> None:
        if await self._client.collection_exists(self.collection):
            return
        await self._client.create_collection(
            collection_name=self.collection,
            vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE),
        )
        # Every query filters by document, so this index is not optional.
        await self._client.create_payload_index(
            collection_name=self.collection,
            field_name="document_id",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )

    async def upsert(self, points: list[ChunkPoint]) -> None:
        if not points:
            return
        await self._client.upsert(
            collection_name=self.collection,
            points=[
                models.PointStruct(
                    id=p.point_id,
                    vector=p.vector,
                    payload={
                        "document_id": str(p.document_id),
                        "block_ids": [str(b) for b in p.block_ids],
                        "text": p.text,
                        "page_no": p.page_no,
                        "section_path": p.section_path,
                    },
                )
                for p in points
            ],
        )

    async def delete_document(self, document_id: uuid.UUID) -> None:
        await self._client.delete(
            collection_name=self.collection,
            points_selector=models.FilterSelector(filter=_document_filter(document_id)),
        )

    async def search(
        self, vector: list[float], document_id: uuid.UUID, limit: int = 8
    ) -> list[SearchHit]:
        if not await self._client.collection_exists(self.collection):
            return []
        result = await self._client.query_points(
            collection_name=self.collection,
            query=vector,
            query_filter=_document_filter(document_id),
            limit=limit,
            with_payload=True,
        )
        hits = []
        for point in result.points:
            payload = point.payload or {}
            hits.append(
                SearchHit(
                    text=payload.get("text", ""),
                    block_ids=[uuid.UUID(b) for b in payload.get("block_ids", [])],
                    page_no=payload.get("page_no", 0),
                    section_path=payload.get("section_path", ""),
                    score=point.score,
                )
            )
        return hits

    async def close(self) -> None:
        await self._client.close()


def _document_filter(document_id: uuid.UUID) -> models.Filter:
    return models.Filter(
        must=[
            models.FieldCondition(
                key="document_id", match=models.MatchValue(value=str(document_id))
            )
        ]
    )
