from dataclasses import dataclass

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.db.models import (
    Classroom,
    ContentVersion,
    SourceChunk as SourceChunkModel,
    SourceDocument,
    TeacherContentPublication,
)
from app.services.rag import SourceChunk
from app.services.persian_text import normalize_persian_text


@dataclass(frozen=True)
class IngestedDocument:
    source_id: str
    chunk_count: int


def split_text(text: str, *, chunk_size: int = 1_500) -> list[str]:
    text = normalize_persian_text(text)
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
    document = await session.scalar(
        select(SourceDocument)
        .options(selectinload(SourceDocument.chunks))
        .where(SourceDocument.source_id == source_id)
    )
    if document is not None:
        document.title = title
        document.uri = uri
        document.chunks.clear()
    else:
        document = SourceDocument(source_id=source_id, title=title, uri=uri)
        session.add(document)
    document.chunks.extend(
        SourceChunkModel(chunk_index=index, text=chunk, page=None)
        for index, chunk in enumerate(chunks)
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
        dialect = self._session.bind.dialect.name if self._session.bind is not None else ""
        if dialect == "postgresql":
            term_filters = [SourceChunkModel.text.ilike(f"%{term}%") for term in terms if len(term) > 2]
            condition = func.similarity(SourceChunkModel.text, query) >= 0.03
            if term_filters:
                condition = or_(condition, *term_filters)
            ranked_result = await self._session.execute(
                select(SourceChunkModel)
                .options(joinedload(SourceChunkModel.document))
                .join(SourceDocument)
                .where(condition)
                .order_by(func.similarity(SourceChunkModel.text, query).desc())
                .limit(limit)
            )
            ranked_chunks = list(ranked_result.scalars().all())
            return [
                SourceChunk(
                    text=chunk.text,
                    source_id=chunk.document.source_id,
                    page=chunk.page,
                    chunk_id=chunk.id,
                    source_type=chunk.source_type,
                    grade=chunk.grade,
                    subject=chunk.subject,
                    book_id=chunk.book_id,
                    score=float(getattr(chunk, "_retrieval_score", 0.0) or 0.0),
                )
                for chunk in ranked_chunks
            ]
        filters = [SourceChunkModel.text.ilike(f"%{term}%") for term in terms]
        result = await self._session.scalars(
            select(SourceChunkModel)
            .options(joinedload(SourceChunkModel.document))
            .join(SourceDocument)
            .where(or_(*filters))
            .limit(limit * 5)
        )
        ranked = sorted(
            result.all(),
            key=lambda chunk: sum(term in chunk.text.casefold() for term in terms),
            reverse=True,
        )
        return [
            SourceChunk(
                text=chunk.text,
                source_id=chunk.document.source_id,
                page=chunk.page,
                chunk_id=chunk.id,
                source_type=chunk.source_type,
                grade=chunk.grade,
                subject=chunk.subject,
                book_id=chunk.book_id,
                score=float(sum(term in chunk.text.casefold() for term in terms)) / max(len(terms), 1),
            )
            for chunk in ranked[:limit]
            if any(term in chunk.text.casefold() for term in terms)
        ]


class ScopedDatabaseRetriever(DatabaseRetriever):
    """Persistence-backed retriever with scope applied before ranking."""

    def __init__(self, session: AsyncSession, *, tenant_id: str, classroom_id: int, grade: str) -> None:
        super().__init__(session)
        self._tenant_id = tenant_id
        self._classroom_id = classroom_id
        self._grade = grade

    async def retrieve(self, query: str, limit: int = 5) -> list[SourceChunk]:
        terms = {term.casefold() for term in normalize_persian_text(query).split() if term.strip()}
        if not terms or limit < 1:
            return []
        term_filters = [SourceChunkModel.text.ilike(f"%{term}%") for term in terms if len(term) > 1]
        if not term_filters:
            return []
        # Publication, approval, vector and tenant/class/grade predicates are
        # all in the candidate query, before lexical ranking.
        result = await self._session.execute(
            select(SourceChunkModel)
            .join(SourceDocument, SourceDocument.id == SourceChunkModel.document_id)
            .join(ContentVersion, ContentVersion.source_document_id == SourceDocument.id)
            .join(TeacherContentPublication, TeacherContentPublication.content_version_id == ContentVersion.id)
            .join(Classroom, Classroom.id == TeacherContentPublication.classroom_id)
            .where(
                Classroom.tenant_id == self._tenant_id,
                Classroom.id == self._classroom_id,
                SourceChunkModel.grade == self._grade,
                TeacherContentPublication.status == "PUBLISHED",
                ContentVersion.review_state == "APPROVED",
                ContentVersion.processing_state.in_(["PROCESSED", "VALIDATED"]),
                ContentVersion.vector_sync_state.in_(["SYNCED", "VECTOR_SYNCED"]),
                or_(*term_filters),
            )
            .options(joinedload(SourceChunkModel.document))
            .limit(limit * 5)
        )
        rows = result.scalars().all()
        ranked = sorted(
            rows,
            key=lambda row: sum(term in normalize_persian_text(row.text).casefold() for term in terms),
            reverse=True,
        )
        return [
            SourceChunk(
                text=row.text,
                source_id=row.document.source_id,
                page=row.page,
                chunk_id=row.id,
                source_type=row.source_type,
                grade=row.grade,
                subject=row.subject,
                book_id=row.book_id,
            )
            for row in ranked[:limit]
        ]
