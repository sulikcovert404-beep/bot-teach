from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models import SourceChunk as SourceChunkModel
from app.db.models import SourceDocument
from app.services.rag import SourceChunk


@dataclass(frozen=True)
class IngestedDocument:
    source_id: str
    chunk_count: int


def split_text(text: str, *, chunk_size: int = 1_500) -> list[str]:
    if not text.strip() or chunk_size < 1:
        raise ValueError("Text and a positive chunk size are required")
    chunks: list[str] = []
    current: list[str] = []
    current_length = 0
    for word in text.split():
        added_length = len(word) if not current else len(word) + 1
        if current and current_length + added_length > chunk_size:
            chunks.append(" ".join(current))
            current = []
            current_length = 0
        current.append(word)
        current_length += len(word) if not current_length else added_length
    if current:
        chunks.append(" ".join(current))
    return chunks


async def ingest_document(
    session: AsyncSession,
    *,
    source_id: str,
    title: str,
    text: str,
    uri: str | None = None,
    chunk_size: int = 1_500,
) -> IngestedDocument:
    if not source_id.strip() or not title.strip():
        raise ValueError("Source id and title are required")
    chunks = split_text(text, chunk_size=chunk_size)
    document = await session.scalar(select(SourceDocument).where(SourceDocument.source_id == source_id))
    if document is not None:
        document.title = title
        document.uri = uri
        document.chunks.clear()
    else:
        document = SourceDocument(source_id=source_id, title=title, uri=uri)
        session.add(document)
    document.chunks.extend(
        SourceChunkModel(chunk_index=index, text=chunk, page=None) for index, chunk in enumerate(chunks)
    )
    await session.flush()
    return IngestedDocument(source_id=source_id, chunk_count=len(chunks))


class DatabaseRetriever:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def retrieve(self, query: str, limit: int = 5) -> list[SourceChunk]:
        terms = {term.casefold() for term in query.split() if term.strip()}
        if not terms or limit < 1:
            return []
        result = await self._session.scalars(
            select(SourceChunkModel)
            .options(joinedload(SourceChunkModel.document))
            .join(SourceDocument)
        )
        ranked = sorted(
            result.all(),
            key=lambda chunk: sum(term in chunk.text.casefold() for term in terms),
            reverse=True,
        )
        return [
            SourceChunk(text=chunk.text, source_id=chunk.document.source_id, page=chunk.page)
            for chunk in ranked[:limit]
            if any(term in chunk.text.casefold() for term in terms)
        ]
