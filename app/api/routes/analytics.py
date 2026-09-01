from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.auth import get_session
from app.db.models import LearningEvent
from app.security.dependencies import require_user
from app.services.learning_analytics import LearningEventInput, summarize_learning

router = APIRouter(prefix="/analytics", tags=["analytics"])


class LearningSummaryResponse(BaseModel):
    event_count: int
    total_duration_seconds: int
    average_score: float | None


@router.get("/summary", response_model=LearningSummaryResponse)
async def learning_summary(
    subject: str = Depends(require_user),
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> LearningSummaryResponse:
    try:
        user_id = int(subject)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid user identity") from exc
    result = await session.scalars(
        select(LearningEvent)
        .where(LearningEvent.user_id == user_id)
        .order_by(LearningEvent.created_at)
    )
    summary = summarize_learning(
        LearningEventInput(event.event_type, event.duration_seconds, event.score)
        for event in result.all()
    )
    return LearningSummaryResponse(**summary.__dict__)
