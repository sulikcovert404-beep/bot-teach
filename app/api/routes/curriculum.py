from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.routes.auth import get_session
from app.db.models import Book, Chapter

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


@router.get("/books", response_model=list[BookResponse])
async def list_books(session: AsyncSession = Depends(get_session)) -> list[Book]:  # noqa: B008
    result = await session.scalars(
        select(Book)
        .options(selectinload(Book.chapters).selectinload(Chapter.lessons))
        .order_by(Book.id)
    )
    return list(result.all())
