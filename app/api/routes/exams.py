from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.routes.auth import get_session
from app.core.config import get_settings
from app.db.models import Exam, ExamQuestion
from app.domain.entitlements.models import FeatureCode
from app.security.dependencies import require_user
from app.security.entitlements import require_feature_access
from app.services.ai_gateway import GeminiProvider, ModelRouter
from app.services.educational_ai import EducationalAI

router = APIRouter(prefix="/exams", tags=["exams"])


class ExamQuestionRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=2_000)
    options: list[str] = Field(min_length=2, max_length=10)
    correct_option: str = Field(min_length=1, max_length=255)


class ExamRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    questions: list[ExamQuestionRequest] = Field(min_length=1, max_length=100)


class ExamQuestionResponse(BaseModel):
    id: int
    prompt: str
    options: list[str]
    correct_option: str
    position: int


class ExamResponse(BaseModel):
    id: int
    title: str
    questions: list[ExamQuestionResponse]
    generated_content: str | None = None


def _response(exam: Exam) -> ExamResponse:
    return ExamResponse(
        id=exam.id,
        title=exam.title,
        questions=[
            ExamQuestionResponse(
                id=question.id,
                prompt=question.prompt,
                options=question.options.split("\n"),
                correct_option=question.correct_option,
                position=question.position,
            )
            for question in exam.questions
        ],
        generated_content=exam.generated_content,
    )


@router.post("", response_model=ExamResponse, status_code=201)
async def create_exam(
    request: ExamRequest,
    subject: str = Depends(require_user),
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> ExamResponse:
    try:
        user_id = int(subject)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid user identity") from exc
    if any(question.correct_option not in question.options for question in request.questions):
        raise HTTPException(status_code=422, detail="Correct option must be present in options")
    exam = Exam(user_id=user_id, title=request.title)
    exam.questions = [
        ExamQuestion(
            prompt=question.prompt,
            options="\n".join(question.options),
            correct_option=question.correct_option,
            position=index,
        )
        for index, question in enumerate(request.questions, start=1)
    ]
    session.add(exam)
    await session.commit()
    await session.refresh(exam)
    return _response(exam)


@router.get("", response_model=list[ExamResponse])
async def list_exams(
    subject: str = Depends(require_user),
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> list[ExamResponse]:
    try:
        user_id = int(subject)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid user identity") from exc
    result = await session.scalars(
        select(Exam)
        .options(selectinload(Exam.questions))
        .where(Exam.user_id == user_id)
        .order_by(Exam.created_at.desc())
    )
    return [_response(exam) for exam in result.all()]


@router.post("/generate", response_model=ExamResponse, status_code=201)
async def generate_and_save_exam(
    request: ExamRequest,
    subject: str = Depends(require_feature_access(FeatureCode.EXAM_GENERATOR)),
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> ExamResponse:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise HTTPException(status_code=503, detail="AI provider unavailable")
    result = await EducationalAI(
        GeminiProvider(settings.gemini_api_key), ModelRouter(settings.ai_default_model)
    ).generate_exam(
        "\n".join(question.prompt for question in request.questions),
        count=len(request.questions),
    )
    exam = Exam(user_id=int(subject), title=request.title, generated_content=result.text)
    session.add(exam)
    await session.commit()
    await session.refresh(exam)
    return _response(exam)
