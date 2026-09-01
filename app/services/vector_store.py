from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SourceChunk as SourceChunkModel
from app.services.rag import SourceChunk


@dataclass(frozen=True)
class VectorSearchRequest:
    embedding: list[float]
    limit: int = 5
    source_type: str | None = None
    book_id: int | None = None
    grade: str | None = None
    subject: str | None = None


class VectorStore(Protocol):
    async def upsert_embedding(
        self, *, chunk_id: int, embedding: list[float], embedding_model: str
    ) -> None: ...

    async def search(self, request: VectorSearchRequest) -> list[SourceChunk]: ...


class PgVectorStore:
    """PostgreSQL pgvector adapter behind the provider-neutral VectorStore contract."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _require_postgresql(self) -> None:
        dialect = self._session.bind.dialect.name if self._session.bind is not None else ""
        if dialect != "postgresql":
            raise RuntimeError("PgVectorStore requires a PostgreSQL session")

    async def upsert_embedding(
        self, *, chunk_id: int, embedding: list[float], embedding_model: str
    ) -> None:
        self._require_postgresql()
        if not embedding or not embedding_model.strip():
            raise ValueError("Embedding and embedding model are required")
        chunk = await self._session.get(SourceChunkModel, chunk_id)
        if chunk is None:
            raise ValueError("Source chunk was not found")
        chunk.embedding = embedding
        chunk.embedding_model = embedding_model
        await self._session.flush()

    async def search(self, request: VectorSearchRequest) -> list[SourceChunk]:
        self._require_postgresql()
        if not request.embedding or not 1 <= request.limit <= 100:
            raise ValueError("Embedding and search limit are invalid")
        distance = SourceChunkModel.embedding.cosine_distance(request.embedding).label("distance")
        query = select(SourceChunkModel, distance).where(SourceChunkModel.embedding.is_not(None))
        for field, value in (
            (SourceChunkModel.source_type, request.source_type),
            (SourceChunkModel.book_id, request.book_id),
            (SourceChunkModel.grade, request.grade),
            (SourceChunkModel.subject, request.subject),
        ):
            if value is not None:
                query = query.where(field == value)
        result = await self._session.execute(query.order_by(distance).limit(request.limit))
        return [
            SourceChunk(
                text=chunk.text,
                source_id=chunk.document.source_id,
                page=chunk.page,
                score=1.0 - float(distance_value),
            )
            for chunk, distance_value in result.all()
        ]
