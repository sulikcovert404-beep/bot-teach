import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.routes.auth import get_session
from app.core.config import get_settings
from app.db.models import (
    Assignment,
    AssignmentTarget,
    AuditLog,
    ClassMembership,
    Classroom,
    Exam,
    ExamQuestion,
    StudentProfile,
)
from app.domain.entitlements.models import FeatureCode
from app.security.dependencies import require_roles, require_user
from app.security.entitlements import require_feature_access
from app.security.tenant_resolver import TenantResolutionError, resolve_tenant
from app.services.ai_gateway import (
    GeminiProvider,
    ModelRouter,
    StructuredLoggingAIProviderObserver,
)
from app.services.audit_repository import record_audit_log
from app.services.educational_ai import EducationalAI
from app.services.exam_attempts import ExamAccessError, save_answers, start_attempt, submit_attempt
from app.services.usage_repository import record_usage

router = APIRouter(prefix="/exams", tags=["assessment-exam-engine"])


# --- Schemas ---

class ExamQuestionRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=2_000)
    options: list[str] = Field(min_length=2, max_length=10)
    correct_option: str = Field(min_length=1, max_length=255)


class ExamRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    questions: list[ExamQuestionRequest] = Field(min_length=1, max_length=100)


class ExamGenerationRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    text: str = Field(min_length=1, max_length=20_000)
    count: int = Field(default=10, ge=1, le=50)
    max_tokens: int = Field(default=2_400, ge=1, le=4_000)


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
    correction_content: str | None = None


class ExamCorrectionRequest(BaseModel):
    answer_key: str = Field(min_length=1, max_length=10_000)
    answers: str = Field(min_length=1, max_length=10_000)
    max_tokens: int = Field(default=1_200, ge=1, le=4_000)


class BankQuestionCreateRequest(BaseModel):
    subject: str = Field(min_length=1, max_length=128)
    chapter: str = Field(min_length=1, max_length=255)
    difficulty: str = Field(default="متوسط", max_length=32)
    question_type: str = Field(default="چهارگزینه‌ای", max_length=64)
    prompt: str = Field(min_length=1, max_length=2_000)
    options: list[str] = Field(min_length=2, max_length=10)
    correct_option: str = Field(min_length=1, max_length=255)
    detailed_solution: str = Field(min_length=1, max_length=4_000)
    source_book_ref: str = Field(default="کتاب درسی رسمی", max_length=255)


class CustomExamBuildRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    subject: str = Field(min_length=1, max_length=128)
    grade: str = Field(default="دهم", max_length=64)
    difficulty_level: str = Field(default="متوسط", max_length=32)
    time_limit_minutes: int = Field(default=30, ge=5, le=240)
    question_ids: list[int] = Field(default=[])


class StudentAnswerSubmission(BaseModel):
    question_id: int
    selected_option: str


class StudentExamSubmitRequest(BaseModel):
    answers: list[StudentAnswerSubmission]


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
        correction_content=exam.correction_content,
    )


# --- 1. Question Bank Operations ---

@router.get("/bank")
async def list_question_bank(
    subject: str = Query(default=None),
    chapter: str = Query(default=None),
    difficulty: str = Query(default=None),
    _user_sub: str = Depends(require_user),
    session: AsyncSession = Depends(get_session),
):
    # Retrieve question bank records from AuditLog
    logs = (
        await session.execute(
            select(AuditLog)
            .where(AuditLog.action == "QUESTION_BANK_ITEM_CREATE")
            .order_by(desc(AuditLog.id))
        )
    ).scalars().all()

    items = []
    for l in logs:
        try:
            items.append(json.loads(l.metadata_json))
        except (json.JSONDecodeError, TypeError):
            pass

    # Empty storage is an honest empty state; sample questions belong in fixtures.
    if not items:
        return {"total_questions": 0, "questions": []}

    # Filter
    if subject:
        items = [q for q in items if subject in q.get("subject", "")]
    if chapter:
        items = [q for q in items if chapter in q.get("chapter", "")]
    if difficulty:
        items = [q for q in items if difficulty == q.get("difficulty")]

    return {"total_questions": len(items), "questions": items}


@router.post("/bank", status_code=201)
async def add_question_to_bank(
    req: BankQuestionCreateRequest,
    teacher_sub: str = Depends(require_roles("TEACHER", "ADMIN")),
    session: AsyncSession = Depends(get_session),
):
    teacher_id = int(teacher_sub)
    q_id = int(datetime.utcnow().timestamp())  # noqa: DTZ003
    q_data = {
        "id": q_id,
        "subject": req.subject,
        "chapter": req.chapter,
        "difficulty": req.difficulty,
        "question_type": req.question_type,
        "prompt": req.prompt,
        "options": req.options,
        "correct_option": req.correct_option,
        "detailed_solution": req.detailed_solution,
        "source_book_ref": req.source_book_ref,
        "author_id": teacher_id,
        "created_at": datetime.utcnow().isoformat(),  # noqa: DTZ003
    }
    await record_audit_log(
        session,
        actor_user_id=teacher_id,
        action="QUESTION_BANK_ITEM_CREATE",
        resource_type="question_bank",
        resource_id=str(q_id),
        metadata=q_data,
    )
    await session.commit()
    return {"status": "created", "question": q_data}


# --- 2. Exam Builder (Teacher/Admin) ---

@router.post("/builder", status_code=201)
async def build_custom_exam(
    req: CustomExamBuildRequest,
    teacher_sub: str = Depends(require_roles("TEACHER", "ADMIN")),
    session: AsyncSession = Depends(get_session),
):
    _teacher_id = int(teacher_sub)

    if not req.question_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one persisted question_id is required",
        )
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Exam builder question-bank integration is not available",
    )



# --- 3. Auto Evaluation & Student Exam Experience ---

@router.post("/{exam_id}/submit")
async def submit_student_exam(
    exam_id: int,
    req: StudentExamSubmitRequest,
    subject: str = Depends(require_user),
    session: AsyncSession = Depends(get_session),
):
    student_id = int(subject)
    # Legacy compatibility path must resolve an authorized Assignment first.
    row = await session.execute(
        select(Assignment).join(AssignmentTarget, AssignmentTarget.assignment_id == Assignment.id)
        .join(Classroom, Classroom.id == AssignmentTarget.classroom_id)
        .join(ClassMembership, ClassMembership.classroom_id == Classroom.id)
        .join(StudentProfile, StudentProfile.id == ClassMembership.student_id)
        .where(Assignment.exam_id == exam_id, StudentProfile.student_id == student_id,
               Assignment.status == "PUBLISHED", Classroom.tenant_id == Assignment.tenant_id)
        .limit(2)
    )
    assignments = row.scalars().all()
    if len(assignments) != 1:
        raise HTTPException(status_code=403, detail="No unique authorized exam assignment")
    assignment = assignments[0]
    try:
        attempt = await start_attempt(session, assignment_id=assignment.id, student_id=student_id, tenant_id=assignment.tenant_id)
        answers = {str(a.question_id): a.selected_option for a in req.answers}
        await save_answers(session, attempt_id=attempt.id, student_id=student_id, tenant_id=assignment.tenant_id, answers=answers)
        result = await submit_attempt(session, attempt_id=attempt.id, student_id=student_id, tenant_id=assignment.tenant_id)
        await session.commit()
    except ExamAccessError as exc:
        await session.rollback()
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return {"exam_id": exam_id, "attempt_id": attempt.id, "result_id": result.id,
            "score": result.score, "max_score": result.max_score, "grading_source": result.grading_source}


# --- 4. Exam Intelligence & Teacher Aggregation ---

@router.get("/{exam_id}/intelligence")
async def get_exam_intelligence(
    exam_id: int,
    _teacher_sub: str = Depends(require_roles("TEACHER", "ADMIN")),
    session: AsyncSession = Depends(get_session),
):
    try:
        actor_id = int(_teacher_sub)
        tenant_id = await resolve_tenant(session, user_id=actor_id)
    except (TypeError, ValueError, TenantResolutionError) as exc:
        raise HTTPException(status_code=403, detail="Tenant scope denied") from exc
    exam = await session.scalar(
        select(Exam)
        .join(Assignment, Assignment.exam_id == Exam.id)
        .where(
            Exam.id == exam_id,
            Exam.tenant_id == tenant_id,
            Assignment.tenant_id == tenant_id,
            Assignment.teacher_id == actor_id,
        )
    )
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    return {
        "exam_id": exam_id,
        "exam_title": exam.title,
        "cohort_metrics": None,
        "question_difficulty_breakdown": [],
        "pedagogical_action_plan": None,
    }


# --- Original Endpoints preserved ---

@router.post("", response_model=ExamResponse, status_code=201)
async def create_exam(
    request: ExamRequest,
    subject: str = Depends(require_user),
    session: AsyncSession = Depends(get_session),
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
    session: AsyncSession = Depends(get_session),
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
    request: ExamGenerationRequest,
    subject: str = Depends(require_feature_access(FeatureCode.EXAM_GENERATOR)),
    session: AsyncSession = Depends(get_session),
) -> ExamResponse:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise HTTPException(status_code=503, detail="AI provider unavailable")
    result = await EducationalAI(
        GeminiProvider(
            settings.gemini_api_key,
            observer=StructuredLoggingAIProviderObserver(),
        ),
        ModelRouter(settings.ai_default_model),
    ).generate_exam(
        request.text,
        count=request.count,
        max_tokens=request.max_tokens,
    )
    exam = Exam(user_id=int(subject), title=request.title, generated_content=result.text)
    session.add(exam)
    await record_usage(
        session,
        user_id=int(subject),
        task_type="exam_generator",
        model=result.model,
        requested_tokens=request.max_tokens,
        charged_tokens=(
            min(result.usage_tokens, request.max_tokens)
            if result.usage_tokens is not None
            else request.max_tokens
        ),
    )
    await session.commit()
    await session.refresh(exam)
    return _response(exam)


@router.post("/{exam_id}/correct", response_model=ExamResponse)
async def correct_saved_exam(
    exam_id: int,
    request: ExamCorrectionRequest,
    subject: str = Depends(require_feature_access(FeatureCode.EXAM_CORRECTOR)),
    session: AsyncSession = Depends(get_session),
) -> ExamResponse:
    exam = await session.scalar(
        select(Exam)
        .options(selectinload(Exam.questions))
        .where(Exam.id == exam_id, Exam.user_id == int(subject))
    )
    if exam is None:
        raise HTTPException(status_code=404, detail="Exam not found")
    settings = get_settings()
    if not settings.gemini_api_key:
        raise HTTPException(status_code=503, detail="AI provider unavailable")
    result = await EducationalAI(
        GeminiProvider(
            settings.gemini_api_key,
            observer=StructuredLoggingAIProviderObserver(),
        ),
        ModelRouter(settings.ai_default_model),
    ).correct_exam(request.answer_key, request.answers, max_tokens=request.max_tokens)
    exam.correction_content = result.text
    await record_usage(
        session,
        user_id=int(subject),
        task_type="exam_corrector",
        model=result.model,
        requested_tokens=request.max_tokens,
        charged_tokens=(
            min(result.usage_tokens, request.max_tokens)
            if result.usage_tokens is not None
            else request.max_tokens
        ),
    )
    await session.commit()
    return _response(exam)
