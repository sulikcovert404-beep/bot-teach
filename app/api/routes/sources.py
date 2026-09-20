from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.auth import get_session
from app.db.base import set_tenant_context
from app.db.models import ClassMembership, Classroom, StudentProfile, TeacherProfile
from app.domain.entitlements.models import FeatureCode
from app.security.dependencies import require_roles
from app.security.entitlements import require_feature_access
from app.services.document_ingestion import ScopedDatabaseRetriever, ingest_document

router = APIRouter(prefix="/sources", tags=["sources"])


class IngestRequest(BaseModel):
    source_id: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=255)
    text: str = Field(min_length=1, max_length=1_000_000)
    uri: str | None = Field(default=None, max_length=2_000)

    @field_validator("uri")
    @classmethod
    def validate_uri(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Source URI must be an absolute http or https URL")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Source URI must not contain embedded credentials")
        return value


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
    session: AsyncSession = Depends(get_session),
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
    classroom_id: int = Query(..., ge=1),
    grade: str = Query(..., min_length=1, max_length=64),
    _subject: str = Depends(require_feature_access(FeatureCode.BOOK_QA)),
    session: AsyncSession = Depends(get_session),
) -> list[SourceChunkResponse]:
    try:
        user_id = int(_subject)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid user identity") from exc
    classroom = await session.scalar(select(Classroom).where(Classroom.id == classroom_id))
    if classroom is None:
        raise HTTPException(status_code=404, detail="Classroom not found")
    teacher_access = await session.scalar(
        select(TeacherProfile.id).where(
            TeacherProfile.teacher_id == user_id,
            TeacherProfile.tenant_id == classroom.tenant_id,
        )
    )
    student_access = await session.scalar(
        select(ClassMembership.id)
        .join(StudentProfile, StudentProfile.id == ClassMembership.student_id)
        .where(
            ClassMembership.classroom_id == classroom_id,
            StudentProfile.student_id == user_id,
        )
    )
    if teacher_access is None and student_access is None:
        raise HTTPException(status_code=403, detail="Classroom access denied")
    await set_tenant_context(session, classroom.tenant_id)
    chunks = await ScopedDatabaseRetriever(
        session, tenant_id=classroom.tenant_id, classroom_id=classroom_id, grade=grade
    ).retrieve(query, limit=limit)
    return [SourceChunkResponse(**chunk.__dict__) for chunk in chunks]
