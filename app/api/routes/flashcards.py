from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.auth import get_session
from app.db.models import Flashcard
from app.security.dependencies import require_user

router = APIRouter(prefix="/flashcards", tags=["flashcards"])


class FlashcardCreate(BaseModel):
    front: str = Field(min_length=1, max_length=2_000)
    back: str = Field(min_length=1, max_length=4_000)
    book_id: int | None = Field(default=None, ge=1)


class FlashcardResponse(BaseModel):
    id: int
    front: str
    back: str
    book_id: int | None


@router.post("", response_model=FlashcardResponse, status_code=status.HTTP_201_CREATED)
async def create_flashcard(
    request: FlashcardCreate,
    subject: str = Depends(require_user),
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> Flashcard:
    try:
        user_id = int(subject)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid user identity") from exc
    card = Flashcard(user_id=user_id, front=request.front, back=request.back, book_id=request.book_id)
    session.add(card)
    await session.commit()
    await session.refresh(card)
    return card


@router.get("", response_model=list[FlashcardResponse])
async def list_flashcards(
    subject: str = Depends(require_user),
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> list[Flashcard]:
    try:
        user_id = int(subject)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid user identity") from exc
    result = await session.scalars(
        select(Flashcard).where(Flashcard.user_id == user_id).order_by(Flashcard.id)
    )
    return list(result.all())
