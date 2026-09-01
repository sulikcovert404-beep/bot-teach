from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.routes.auth import get_session
from app.db.models import Book, Chapter, Lesson
from app.security.dependencies import require_roles

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
async def list_books(session: AsyncSession = Depends(get_session)) -> list[Book]:  # noqa: B008
    result = await session.scalars(
        select(Book)
        .options(selectinload(Book.chapters).selectinload(Chapter.lessons))
        .order_by(Book.id)
    )
    return list(result.all())


@router.post("/books", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
async def create_book(
    request: BookCreate,
    _subject: str = Depends(require_roles("ADMIN", "TEACHER")),
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> Book:
    book = Book(title=request.title, grade=request.grade, subject=request.subject)
    session.add(book)
    await session.commit()
    await session.refresh(book)
    return book


@router.post("/books/{book_id}/chapters", response_model=ChapterResponse, status_code=status.HTTP_201_CREATED)
async def create_chapter(
    book_id: int,
    request: ChapterCreate,
    _subject: str = Depends(require_roles("ADMIN", "TEACHER")),
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> Chapter:
    book = await session.get(Book, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    chapter = Chapter(book_id=book_id, title=request.title, position=request.position)
    session.add(chapter)
    await session.commit()
    await session.refresh(chapter)
    return chapter


@router.post("/chapters/{chapter_id}/lessons", response_model=LessonResponse, status_code=status.HTTP_201_CREATED)
async def create_lesson(
    chapter_id: int,
    request: LessonCreate,
    _subject: str = Depends(require_roles("ADMIN", "TEACHER")),
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> Lesson:
    chapter = await session.get(Chapter, chapter_id)
    if chapter is None:
        raise HTTPException(status_code=404, detail="Chapter not found")
    lesson = Lesson(chapter_id=chapter_id, title=request.title, position=request.position)
    session.add(lesson)
    await session.commit()
    await session.refresh(lesson)
    return lesson
