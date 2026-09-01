from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.auth import get_session
from app.domain.entitlements.models import FeatureCode
from app.security.dependencies import require_roles
from app.security.entitlements import require_feature_access
from app.services.document_ingestion import DatabaseRetriever, ingest_document

router = APIRouter(prefix="/sources", tags=["sources"])


class IngestRequest(BaseModel):
    source_id: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=255)
    text: str = Field(min_length=1, max_length=1_000_000)
    uri: str | None = Field(default=None, max_length=2_000)


class IngestResponse(BaseModel):
    source_id: str
    chunk_count: int


class SourceChunkResponse(BaseModel):
    text: str
    source_id: str
    page: int | None


@router.post("", response_model=IngestResponse)
async def ingest_source(
    request: IngestRequest,
    _subject: str = Depends(require_roles("ADMIN", "TEACHER")),
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> IngestResponse:
    result = await ingest_document(
        session,
        source_id=request.source_id,
        title=request.title,
        text=request.text,
        uri=request.uri,
    )
    await session.commit()
    return IngestResponse(**result.__dict__)


@router.get("/search", response_model=list[SourceChunkResponse])
async def search_sources(
    query: str = Query(min_length=1, max_length=500),
    limit: int = Query(default=5, ge=1, le=20),
    _subject: str = Depends(require_feature_access(FeatureCode.BOOK_QA)),
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> list[SourceChunkResponse]:
    chunks = await DatabaseRetriever(session).retrieve(query, limit=limit)
    return [SourceChunkResponse(**chunk.__dict__) for chunk in chunks]
