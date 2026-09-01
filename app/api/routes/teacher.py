from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.domain.entitlements.models import FeatureCode
from app.security.entitlements import require_feature_access
from app.services.ai_gateway import GeminiProvider, ModelRouter
from app.services.teacher_assistant import TeacherAssistant

router = APIRouter(prefix="/teacher", tags=["teacher-assistant"])


class LessonPlanRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=2_000)
    grade: str = Field(min_length=1, max_length=64)
    minutes: int = Field(default=45, ge=10, le=240)
    max_tokens: int = Field(default=1_600, ge=1, le=4_000)


class LessonPlanResponse(BaseModel):
    text: str
    model: str
    task_type: str = "teacher_assistant"


@router.post("/lesson-plan", response_model=LessonPlanResponse)
async def create_lesson_plan(
    request: LessonPlanRequest,
    _subject: str = Depends(require_feature_access(FeatureCode.TEACHER_ASSISTANT)),
) -> LessonPlanResponse:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI provider unavailable",
        )
    result = await TeacherAssistant(
        GeminiProvider(settings.gemini_api_key), ModelRouter(settings.ai_default_model)
    ).create_lesson_plan(
        request.topic,
        grade=request.grade,
        minutes=request.minutes,
        max_tokens=request.max_tokens,
    )
    return LessonPlanResponse(text=result.text, model=result.model)
