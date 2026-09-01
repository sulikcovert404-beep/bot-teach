from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.auth import get_session
from app.core.config import get_settings
from app.domain.entitlements.models import FeatureCode
from app.security.entitlements import require_feature_access
from app.services.ai_gateway import AIRequest, GeminiProvider, ModelRouter
from app.services.educational_ai import EducationalAI
from app.services.usage_repository import record_usage

router = APIRouter(prefix="/ai", tags=["ai"])


class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=20_000)
    model: str | None = None
    max_tokens: int = Field(default=1000, ge=1, le=4000)
    task_type: str = Field(default="general", min_length=1, max_length=64)


class GenerateResponse(BaseModel):
    text: str
    model: str
    task_type: str


class SummarizeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=20_000)
    max_tokens: int = Field(default=800, ge=1, le=4000)


class QuestionsRequest(BaseModel):
    text: str = Field(min_length=1, max_length=20_000)
    count: int = Field(default=5, ge=1, le=20)
    max_tokens: int = Field(default=1200, ge=1, le=4000)


class ExamRequest(BaseModel):
    text: str = Field(min_length=1, max_length=20_000)
    count: int = Field(default=10, ge=1, le=50)
    max_tokens: int = Field(default=2400, ge=1, le=4000)


class ExamCorrectionRequest(BaseModel):
    answer_key: str = Field(min_length=1, max_length=10_000)
    answers: str = Field(min_length=1, max_length=10_000)
    max_tokens: int = Field(default=1200, ge=1, le=4000)


async def _record_ai_usage(
    session: AsyncSession,
    subject: str,
    *,
    task_type: str,
    model: str,
    requested_tokens: int,
    usage_tokens: int | None,
) -> None:
    try:
        user_id = int(subject)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user identity") from exc
    await record_usage(
        session,
        user_id=user_id,
        task_type=task_type,
        model=model,
        requested_tokens=requested_tokens,
        charged_tokens=min(usage_tokens, requested_tokens) if usage_tokens is not None else requested_tokens,
    )
    await session.commit()


@router.post("/generate", response_model=GenerateResponse)
async def generate(
    request: GenerateRequest,
    subject: str = Depends(require_feature_access(FeatureCode.AI_CHAT)),
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> GenerateResponse:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI provider unavailable")
    try:
        routed = ModelRouter(settings.ai_default_model).route(
            AIRequest(
                prompt=request.prompt,
                model=request.model,
                max_tokens=request.max_tokens,
                task_type=request.task_type,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    try:
        result = await GeminiProvider(settings.gemini_api_key).generate(routed)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI provider unavailable") from exc
    await _record_ai_usage(
        session,
        subject,
        task_type=request.task_type,
        model=result.model,
        requested_tokens=routed.max_tokens,
        usage_tokens=result.usage_tokens,
    )
    return GenerateResponse(text=result.text, model=result.model, task_type=request.task_type)


def _educational_ai() -> EducationalAI:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI provider unavailable")
    return EducationalAI(GeminiProvider(settings.gemini_api_key), ModelRouter(settings.ai_default_model))


@router.post("/summarize", response_model=GenerateResponse)
async def summarize(
    request: SummarizeRequest,
    subject: str = Depends(require_feature_access(FeatureCode.SMART_SUMMARY)),
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> GenerateResponse:
    try:
        result = await _educational_ai().summarize(request.text, max_tokens=request.max_tokens)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI provider unavailable") from exc
    await _record_ai_usage(session, subject, task_type="smart_summary", model=result.model,
                           requested_tokens=request.max_tokens, usage_tokens=result.usage_tokens)
    return GenerateResponse(text=result.text, model=result.model, task_type="smart_summary")


@router.post("/questions", response_model=GenerateResponse)
async def generate_questions(
    request: QuestionsRequest,
    subject: str = Depends(require_feature_access(FeatureCode.QUESTION_GENERATOR)),
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> GenerateResponse:
    try:
        result = await _educational_ai().generate_questions(
            request.text, count=request.count, max_tokens=request.max_tokens
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI provider unavailable") from exc
    await _record_ai_usage(session, subject, task_type="question_generator", model=result.model,
                           requested_tokens=request.max_tokens, usage_tokens=result.usage_tokens)
    return GenerateResponse(text=result.text, model=result.model, task_type="question_generator")


@router.post("/exam", response_model=GenerateResponse)
async def generate_exam(
    request: ExamRequest,
    subject: str = Depends(require_feature_access(FeatureCode.EXAM_GENERATOR)),
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> GenerateResponse:
    try:
        result = await _educational_ai().generate_exam(
            request.text, count=request.count, max_tokens=request.max_tokens
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI provider unavailable") from exc
    await _record_ai_usage(session, subject, task_type="exam_generator", model=result.model,
                           requested_tokens=request.max_tokens, usage_tokens=result.usage_tokens)
    return GenerateResponse(text=result.text, model=result.model, task_type="exam_generator")


@router.post("/exam/correct", response_model=GenerateResponse)
async def correct_exam(
    request: ExamCorrectionRequest,
    subject: str = Depends(require_feature_access(FeatureCode.EXAM_CORRECTOR)),
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> GenerateResponse:
    try:
        result = await _educational_ai().correct_exam(
            request.answer_key, request.answers, max_tokens=request.max_tokens
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI provider unavailable") from exc
    await _record_ai_usage(session, subject, task_type="exam_corrector", model=result.model,
                           requested_tokens=request.max_tokens, usage_tokens=result.usage_tokens)
    return GenerateResponse(text=result.text, model=result.model, task_type="exam_corrector")
