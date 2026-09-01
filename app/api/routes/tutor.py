from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.auth import get_session
from app.core.config import get_settings
from app.domain.entitlements.models import FeatureCode
from app.security.entitlements import require_feature_access
from app.services.ai_gateway import GeminiProvider, ModelRouter
from app.services.ai_tutor import AITutor
from app.services.document_ingestion import DatabaseRetriever

router = APIRouter(prefix="/tutor", tags=["ai-tutor"])


class TutorRequest(BaseModel):
    query: str = Field(min_length=1, max_length=10_000)
    max_tokens: int = Field(default=1_200, ge=1, le=4_000)


class TutorResponse(BaseModel):
    text: str
    model: str
    task_type: str = "ai_tutor"


@router.post("/answer", response_model=TutorResponse)
async def tutor_answer(
    request: TutorRequest,
    _subject: str = Depends(require_feature_access(FeatureCode.BOOK_QA)),
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> TutorResponse:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI provider unavailable")
    try:
        result = await AITutor(
            GeminiProvider(settings.gemini_api_key),
            ModelRouter(settings.ai_default_model),
            DatabaseRetriever(session),
        ).answer(request.query, max_tokens=request.max_tokens)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI provider unavailable") from exc
    return TutorResponse(text=result.text, model=result.model)
