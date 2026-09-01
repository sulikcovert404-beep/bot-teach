from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.routes.auth import get_session
from app.db.models import Book, Chapter, Lesson
from app.security.dependencies import require_roles
from app.services.audit_repository import record_audit_log

router = APIRouter(prefix="/curriculum", tags=["curriculum"])


class LessonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    position: int


class ChapterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    position: int
    lessons: list[LessonResponse]


class BookResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    grade: str | None
    subject: str | None
    chapters: list[ChapterResponse]


class BookCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    grade: str | None = Field(default=None, max_length=64)
    subject: str | None = Field(default=None, max_length=128)


class ChapterCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    position: int = Field(default=0, ge=0)


class LessonCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    position: int = Field(default=0, ge=0)


@router.get("/books", response_model=list[BookResponse])
async def list_books(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> list[Book]:
    result = await session.scalars(
        select(Book)
        .options(selectinload(Book.chapters).selectinload(Chapter.lessons))
        .order_by(Book.id)
        .offset(offset)
        .limit(limit)
    )
    return list(result.all())


@router.post("/books", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
async def create_book(
    request: BookCreate,
    subject: str = Depends(require_roles("ADMIN", "TEACHER")),
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> Book:
    book = Book(title=request.title, grade=request.grade, subject=request.subject)
    session.add(book)
    await session.flush()
    await session.refresh(book)
    await record_audit_log(
        session,
        actor_user_id=int(subject),
        action="curriculum_book_created",
        resource_type="book",
        resource_id=str(book.id),
        metadata={"title": book.title},
    )
    await session.commit()
    return book


@router.post("/books/{book_id}/chapters", response_model=ChapterResponse, status_code=status.HTTP_201_CREATED)
async def create_chapter(
    book_id: int,
    request: ChapterCreate,
    subject: str = Depends(require_roles("ADMIN", "TEACHER")),
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> Chapter:
    book = await session.get(Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    chapter = Chapter(book_id=book_id, title=request.title, position=request.position)
    session.add(chapter)
    await session.flush()
    await session.refresh(chapter)
    await record_audit_log(
        session,
        actor_user_id=int(subject),
        action="curriculum_chapter_created",
        resource_type="chapter",
        resource_id=str(chapter.id),
        metadata={"book_id": book_id, "title": chapter.title},
    )
    await session.commit()
    return chapter


@router.post("/chapters/{chapter_id}/lessons", response_model=LessonResponse, status_code=status.HTTP_201_CREATED)
async def create_lesson(
    chapter_id: int,
    request: LessonCreate,
    subject: str = Depends(require_roles("ADMIN", "TEACHER")),
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> Lesson:
    chapter = await session.get(Chapter, chapter_id)
    if chapter is None:
        raise HTTPException(status_code=404, detail="Chapter not found")
    lesson = Lesson(chapter_id=chapter_id, title=request.title, position=request.position)
    session.add(lesson)
    await session.flush()
    await session.refresh(lesson)
    await record_audit_log(
        session,
        actor_user_id=int(subject),
        action="curriculum_lesson_created",
        resource_type="lesson",
        resource_id=str(lesson.id),
        metadata={"chapter_id": chapter_id, "title": lesson.title},
    )
    await session.commit()
    return lesson
