from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.auth import get_session
from app.db.models import LearningEvent
from app.security.dependencies import require_user
from app.services.adaptive_learning import PracticeLevel, recommend_practice_level
from app.services.learning_analytics import LearningEventInput, LearningSummary, summarize_learning

router = APIRouter(prefix="/analytics", tags=["analytics"])


class LearningSummaryResponse(BaseModel):
    event_count: int
    total_duration_seconds: int
    average_score: float | None


class LearningEventRequest(BaseModel):
    event_type: str = Field(min_length=1, max_length=64)
    duration_seconds: int = Field(default=0, ge=0, le=86_400)
    score: float | None = Field(default=None, ge=0, le=1)

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Event type cannot be blank")
        return normalized


class PracticeRecommendationResponse(BaseModel):
    level: PracticeLevel
    summary: LearningSummaryResponse


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


@router.post("/events", response_model=LearningEventRequest, status_code=201)
async def record_learning_event(
    request: LearningEventRequest,
    subject: str = Depends(require_user),
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> LearningEventRequest:
    try:
        user_id = int(subject)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid user identity") from exc
    session.add(
        LearningEvent(
            user_id=user_id,
            event_type=request.event_type,
            duration_seconds=request.duration_seconds,
            score=request.score,
        )
    )
    await session.commit()
    return request


@router.get("/recommendation", response_model=PracticeRecommendationResponse)
async def practice_recommendation(
    subject: str = Depends(require_user),
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> PracticeRecommendationResponse:
    summary = await learning_summary(subject, session)
    learning = LearningSummary(
        event_count=summary.event_count,
        total_duration_seconds=summary.total_duration_seconds,
        average_score=summary.average_score,
    )
    return PracticeRecommendationResponse(
        level=recommend_practice_level(learning), summary=summary
    )
