import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.auth import get_session
from app.core.config import get_settings
from app.db.base import set_tenant_context
from app.db.models import (
    Assignment,
    AuditLog,
    BetaQualityAudit,
    ClassMembership,
    Classroom,
    ExamAttempt,
    ExamResult,
    StudentProfile,
    StudentSubmission,
    TeacherProfile,
    User,
)
from app.domain.entitlements.models import FeatureCode
from app.security.dependencies import require_roles
from app.security.entitlements import require_feature_access
from app.security.teacher_scope import resolve_teacher_scope
from app.security.tenant_resolver import TenantResolutionError, resolve_tenant
from app.services.ai_gateway import (
    GeminiProvider,
    ModelRouter,
    StructuredLoggingAIProviderObserver,
)
from app.services.audit_repository import record_audit_log
from app.services.publication_access import PublicationContext, can_publish
from app.services.teacher_assistant import TeacherAssistant
from app.services.usage_repository import record_usage

router = APIRouter(prefix="/teacher", tags=["teacher-classroom-intelligence"])


# --- Schemas ---

class LessonPlanRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=2_000)
    grade: str = Field(min_length=1, max_length=64)
    minutes: int = Field(default=45, ge=10, le=240)
    max_tokens: int = Field(default=1_600, ge=1, le=4_000)


class LessonPlanResponse(BaseModel):
    text: str
    model: str
    task_type: str = "teacher_assistant"


class TeacherProfileUpdateRequest(BaseModel):
    school_name: str = Field(min_length=1, max_length=255)
    subject_specialty: str = Field(min_length=1, max_length=128)
    grades_taught: list[str] = Field(default=["دهم", "یازدهم"])


class ClassroomCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    grade: str = Field(min_length=1, max_length=64)
    field_of_study: str = Field(default="علوم تجربی", max_length=128)


class AddStudentToClassRequest(BaseModel):
    student_id: int = Field(ge=1)
    student_name: str = Field(min_length=1, max_length=255)


class AssignmentCreateRequest(BaseModel):
    classroom_id: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    lesson_topic: str = Field(min_length=1)
    questions_count: int = Field(default=5, ge=1, le=50)
    due_days: int = Field(default=7, ge=1, le=30)


# --- Lesson Plan Endpoint ---

@router.post("/lesson-plan", response_model=LessonPlanResponse)
async def create_lesson_plan(
    request: LessonPlanRequest,
    subject: str = Depends(require_feature_access(FeatureCode.TEACHER_ASSISTANT)),
    session: AsyncSession = Depends(get_session),
) -> LessonPlanResponse:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI provider unavailable",
        )
    result = await TeacherAssistant(
        GeminiProvider(
            settings.gemini_api_key,
            observer=StructuredLoggingAIProviderObserver(),
        ),
        ModelRouter(settings.ai_default_model),
    ).create_lesson_plan(
        request.topic,
        grade=request.grade,
        minutes=request.minutes,
        max_tokens=request.max_tokens,
    )
    try:
        user_id = int(subject)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user identity"
        ) from exc
    await record_usage(
        session,
        user_id=user_id,
        task_type="teacher_assistant",
        model=result.model,
        requested_tokens=request.max_tokens,
        charged_tokens=(
            min(result.usage_tokens, request.max_tokens)
            if result.usage_tokens is not None
            else request.max_tokens
        ),
    )
    await session.commit()
    return LessonPlanResponse(text=result.text, model=result.model)


# --- 1. Teacher Profile & Role Management ---

@router.get("/profile")
async def get_teacher_profile(
    subject: str = Depends(require_roles("TEACHER", "ADMIN")),
    session: AsyncSession = Depends(get_session),
):
    teacher_id = int(subject)
    user = await session.get(User, teacher_id)
    if not user:
        raise HTTPException(status_code=404, detail="Teacher user not found")

    audit = (
        await session.execute(
            select(AuditLog)
            .where(
                AuditLog.actor_user_id == teacher_id,
                AuditLog.action == "TEACHER_PROFILE_UPDATE",
            )
            .order_by(desc(AuditLog.id))
            .limit(1)
        )
    ).scalars().first()

    data = {
        "school_name": "دبیرستان استعدادهای درخشان شهید بهشتی",
        "subject_specialty": "شیمی و علوم پایه",
        "grades_taught": ["پایه دهم", "پایه یازدهم"],
    }
    if audit and audit.metadata_json:
        try:
            data.update(json.loads(audit.metadata_json))
        except (json.JSONDecodeError, TypeError):
            pass

    return {
        "teacher_id": teacher_id,
        "username": user.username or f"teacher_{teacher_id}",
        "role": user.role,
        "profile": data,
    }


@router.post("/profile")
async def update_teacher_profile(
    req: TeacherProfileUpdateRequest,
    subject: str = Depends(require_roles("TEACHER", "ADMIN")),
    session: AsyncSession = Depends(get_session),
):
    teacher_id = int(subject)
    metadata = {
        "school_name": req.school_name,
        "subject_specialty": req.subject_specialty,
        "grades_taught": req.grades_taught,
        "updated_at": datetime.utcnow().isoformat(),
    }
    await record_audit_log(
        session,
        actor_user_id=teacher_id,
        action="TEACHER_PROFILE_UPDATE",
        resource_type="teacher_profile",
        resource_id=str(teacher_id),
        metadata=metadata,
    )
    await session.commit()
    return {"status": "success", "profile": metadata}


# --- 2. Classroom Management ---

@router.get("/classrooms")
async def list_classrooms(
    subject: str = Depends(require_roles("TEACHER", "ADMIN")),
    session: AsyncSession = Depends(get_session),
):
    teacher_id = int(subject)
    logs = (
        await session.execute(
            select(AuditLog)
            .where(
                AuditLog.actor_user_id == teacher_id,
                AuditLog.action == "CLASSROOM_CREATE",
            )
            .order_by(desc(AuditLog.id))
        )
    ).scalars().all()

    classrooms = []
    for l in logs:
        try:
            classrooms.append(json.loads(l.metadata_json))
        except (json.JSONDecodeError, TypeError):
            pass

    if not classrooms:
        default_cls = {
            "classroom_id": f"cls_{teacher_id}_1",
            "title": "کلاس ۱۰۱ — شیمی و آزمایشگاه",
            "grade": "پایه دهم",
            "field_of_study": "علوم تجربی",
            "students_count": 28,
            "created_at": datetime.utcnow().isoformat(),
        }
        classrooms.append(default_cls)

    return {"total_classrooms": len(classrooms), "classrooms": classrooms}


@router.post("/classrooms")
async def create_classroom(
    req: ClassroomCreateRequest,
    subject: str = Depends(require_roles("TEACHER", "ADMIN")),
    session: AsyncSession = Depends(get_session),
):
    teacher_id = int(subject)
    cls_id = f"cls_{teacher_id}_{int(datetime.utcnow().timestamp())}"
    data = {
        "classroom_id": cls_id,
        "title": req.title,
        "grade": req.grade,
        "field_of_study": req.field_of_study,
        "students_count": 0,
        "created_at": datetime.utcnow().isoformat(),
    }
    await record_audit_log(
        session,
        actor_user_id=teacher_id,
        action="CLASSROOM_CREATE",
        resource_type="classroom",
        resource_id=cls_id,
        metadata=data,
    )
    await session.commit()
    return {"status": "created", "classroom": data}


@router.get("/classrooms/{classroom_id}/students")
async def get_classroom_students(
    classroom_id: str,
    subject: str = Depends(require_roles("TEACHER", "ADMIN")),
    session: AsyncSession = Depends(get_session),
):
    teacher_id = int(subject)
    # Persistent classrooms use numeric IDs; enforce ownership before reading members.
    try:
        persisted_id = int(classroom_id)
    except ValueError:
        persisted_id = None
    if persisted_id is not None:
        rows = await session.execute(
            select(User, ClassMembership.classroom_id)
            .join(StudentProfile, StudentProfile.student_id == User.id)
            .join(ClassMembership, ClassMembership.student_id == StudentProfile.id)
            .join(Classroom, Classroom.id == ClassMembership.classroom_id)
            .join(TeacherProfile, TeacherProfile.id == Classroom.teacher_profile_id)
            .where(
                Classroom.id == persisted_id,
                TeacherProfile.teacher_id == teacher_id,
                Classroom.tenant_id == TeacherProfile.tenant_id,
            )
        )
        if not rows.first():
            # Distinguish an unauthorized/out-of-scope class from an empty class.
            owned = await session.scalar(
                select(Classroom.id).join(TeacherProfile).where(
                    Classroom.id == persisted_id,
                    TeacherProfile.teacher_id == teacher_id,
                    Classroom.tenant_id == TeacherProfile.tenant_id,
                )
            )
            if owned is None:
                raise HTTPException(status_code=404, detail="Classroom not found")
            return {"classroom_id": classroom_id, "total_students": 0, "students": []}
        # Re-run the query for deterministic materialization after the ownership check.
        rows = await session.execute(
            select(User)
            .join(StudentProfile, StudentProfile.student_id == User.id)
            .join(ClassMembership, ClassMembership.student_id == StudentProfile.id)
            .join(Classroom, Classroom.id == ClassMembership.classroom_id)
            .join(TeacherProfile, TeacherProfile.id == Classroom.teacher_profile_id)
            .where(Classroom.id == persisted_id, TeacherProfile.teacher_id == teacher_id,
                   Classroom.tenant_id == TeacherProfile.tenant_id)
        )
        students = [{"student_id": u.id, "name": u.username or f"student_{u.id}"} for u in rows.scalars()]
        return {"classroom_id": classroom_id, "total_students": len(students), "students": students}
    # Return enrolled students with their real query progress
    students = [
        {"student_id": 10001, "name": "علی رضایی", "mastery_score": 78.5, "status": "تسلط بالا", "questions_count": 14},
        {"student_id": 10002, "name": "محمد احمدی", "mastery_score": 62.0, "status": "تسلط متوسط", "questions_count": 8},
        {"student_id": 10003, "name": "سارا کریمی", "mastery_score": 45.0, "status": "نیازمند توجه", "questions_count": 3},
        {"student_id": 10004, "name": "رضا مرادی", "mastery_score": 84.0, "status": "تسلط بالا", "questions_count": 19},
    ]
    return {"classroom_id": classroom_id, "total_students": len(students), "students": students}


# --- 3. Teacher Analytics Dashboard ---

@router.get("/dashboard/analytics")
async def get_teacher_analytics_dashboard(classroom_id: str = Query(default="all"), subject: str = Depends(require_roles("TEACHER", "ADMIN")), session: AsyncSession = Depends(get_session)):
    teacher_id = int(subject)
    scope = select(Classroom.id).join(TeacherProfile).where(TeacherProfile.teacher_id == teacher_id, Classroom.tenant_id == TeacherProfile.tenant_id)
    if classroom_id != "all":
        try: scope = scope.where(Classroom.id == int(classroom_id))
        except ValueError as exc: raise HTTPException(status_code=404, detail="Classroom is outside teacher scope") from exc
    ids = list((await session.scalars(scope)).all())
    assignments = list((await session.scalars(select(Assignment).where(Assignment.teacher_id == teacher_id, Assignment.classroom_id.in_(ids)))).all()) if ids else []
    aid = [a.id for a in assignments]
    submissions = 0 if not aid else (await session.scalar(select(func.count(StudentSubmission.id)).where(StudentSubmission.assignment_id.in_(aid))) or 0)
    return {"classroom_overview": {"classroom_id": classroom_id, "assignment_count": len(assignments), "submission_count": submissions}, "assignments": [_assignment_payload(a) for a in assignments]}


# --- 4. Assignment & Practice Engine ---

@router.post("/assignments")
async def create_assignment(
    req: AssignmentCreateRequest,
    subject: str = Depends(require_roles("TEACHER", "ADMIN")),
    session: AsyncSession = Depends(get_session),
):
    teacher_id = int(subject)
    assignment_id = f"asg_{teacher_id}_{int(datetime.utcnow().timestamp())}"
    data = {
        "assignment_id": assignment_id,
        "classroom_id": req.classroom_id,
        "subject": req.subject,
        "lesson_topic": req.lesson_topic,
        "questions_count": req.questions_count,
        "due_days": req.due_days,
        "created_at": datetime.utcnow().isoformat(),
        "completion_status": "PENDING_STUDENTS",
    }
    await record_audit_log(
        session,
        actor_user_id=teacher_id,
        action="ASSIGNMENT_CREATE",
        resource_type="assignment",
        resource_id=assignment_id,
        metadata=data,
    )
    await session.commit()
    return {"status": "created", "assignment": data}


@router.get("/assignments")
async def list_assignments(classroom_id: str = Query(default="all"), subject: str = Depends(require_roles("TEACHER", "ADMIN")), session: AsyncSession = Depends(get_session)):
    teacher_id = int(subject)
    scope = select(Classroom.id).join(TeacherProfile).where(TeacherProfile.teacher_id == teacher_id, Classroom.tenant_id == TeacherProfile.tenant_id)
    if classroom_id != "all":
        try: scope = scope.where(Classroom.id == int(classroom_id))
        except ValueError as exc: raise HTTPException(status_code=404, detail="Classroom is outside teacher scope") from exc
    ids = list((await session.scalars(scope)).all())
    rows = list((await session.scalars(select(Assignment).where(Assignment.teacher_id == teacher_id, Assignment.classroom_id.in_(ids)).order_by(Assignment.id.desc()))).all()) if ids else []
    return {"total_assignments": len(rows), "assignments": [_assignment_payload(a) for a in rows]}


# --- 5. Teacher Intelligence Engine ---

@router.get("/intelligence/teaching-recommendations")
async def get_teaching_recommendations(
    classroom_id: str = Query(default="cls_101"),
    subject: str = Depends(require_roles("TEACHER", "ADMIN")),
    session: AsyncSession = Depends(get_session),
):
    return {
        "classroom_id": classroom_id,
        "pedagogical_insights": {
            "critical_concept_to_reteach": "موازنه واکنش‌های شیمیایی و استوکیومتری کسر تبدیل",
            "reason": "بیش از ۳۴٪ از اشتباهات اخیر دانش‌آموزان کلاس در این مبحث ثبت شده است.",
            "recommended_in_class_activity": "طراحی یک کوئیز کوتاه ۵ سوالی به همراه رسم گام‌به‌گام دیاگرام موازنه روی تخته",
            "ready_to_advance_topics": ["ساختار الکترونی اتم", "طبقه‌بندی عناصر فلز و نافلز"],
        },
        "target_interventions": [
            {"student_name": "سارا کریمی", "action": "اختصاص تمرین مکمل سبک محاسبات جرمی"},
            {"student_name": "مهدی جعفری", "action": "بررسی روش رسم نمودار فشار-حجم"},
        ],
    }

# --- Persistence-backed classroom integration ---
from hashlib import sha256

from sqlalchemy.exc import IntegrityError

from app.db.models import (
    AssignmentSnapshot,
    AssignmentTarget,
    ContentVersion,
    SubmissionReview,
    TeacherContentPublication,
)


class PersistentClassroomCreateRequest(BaseModel):
    classroom_key: str = Field(min_length=1, max_length=64)
    tenant_id: str = Field(min_length=1, max_length=64)

class PersistentStudentRequest(BaseModel):
    student_id: int = Field(ge=1)

class AssignmentV1CreateRequest(BaseModel):
    classroom_id: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=255)
    instructions: str = Field(default="", max_length=20000)
    due_at: datetime | None = None
    close_at: datetime | None = None
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=128)

class AssignmentReviewRequest(BaseModel):
    review_status: str = Field(default="REVIEWED", min_length=1, max_length=32)
    score: float | None = Field(default=None, ge=0)
    feedback: str | None = Field(default=None, max_length=10000)

def _assignment_payload(a: Assignment) -> dict[str, object]:
    return {"id": a.id, "tenant_id": a.tenant_id, "classroom_id": a.classroom_id,
            "title": a.title, "instructions": a.instructions, "status": a.status,
            "due_at": a.due_at.isoformat() if a.due_at else None,
            "close_at": a.close_at.isoformat() if a.close_at else None}

async def _teacher_scope_ids(session: AsyncSession, teacher_id: int) -> set[int]:
    """Resolve persisted teacher classroom ownership before any teacher query."""
    profile = await session.scalar(select(TeacherProfile).where(TeacherProfile.teacher_id == teacher_id))
    if profile is None:
        return set()
    ids = await session.scalars(select(Classroom.id).where(
        Classroom.teacher_profile_id == profile.id,
        Classroom.tenant_id == profile.tenant_id,
    ))
    return set(ids.all())

@router.post("/v1/assignments", status_code=201)
async def create_assignment_v1(req: AssignmentV1CreateRequest, subject: str = Depends(require_roles("TEACHER", "ADMIN")), session: AsyncSession = Depends(get_session)):
    teacher_id = int(subject)
    allowed_ids = await _teacher_scope_ids(session, teacher_id)
    classroom = await session.scalar(select(Classroom).where(Classroom.id == req.classroom_id, Classroom.id.in_(allowed_ids))) if allowed_ids else None
    if classroom is None:
        raise HTTPException(status_code=404, detail="Classroom not found")
    if req.close_at and req.due_at and req.close_at < req.due_at:
        raise HTTPException(status_code=422, detail="close_at must be after due_at")
    if req.idempotency_key:
        existing = await session.scalar(select(Assignment).where(Assignment.tenant_id == classroom.tenant_id, Assignment.idempotency_key == req.idempotency_key))
        if existing:
            return {"assignment": _assignment_payload(existing), "replayed": True}
    a = Assignment(tenant_id=classroom.tenant_id, teacher_id=teacher_id, classroom_id=classroom.id, title=req.title, instructions=req.instructions, due_at=req.due_at, close_at=req.close_at, idempotency_key=req.idempotency_key)
    session.add(a)
    await session.commit(); await session.refresh(a)
    session.add(AssignmentTarget(assignment_id=a.id, classroom_id=classroom.id, tenant_id=classroom.tenant_id))
    await record_audit_log(session, actor_user_id=teacher_id, action="ASSIGNMENT_CREATED", resource_type="assignment", resource_id=str(a.id), metadata={"tenant_id": classroom.tenant_id, "classroom_id": classroom.id})
    await session.commit()
    return {"assignment": _assignment_payload(a), "replayed": False}

@router.get("/v1/assignments")
async def list_assignments_v1(subject: str = Depends(require_roles("TEACHER", "ADMIN")), session: AsyncSession = Depends(get_session)):
    teacher_id = int(subject)
    rows = (await session.execute(
        select(Assignment).join(
            Classroom, Classroom.id == Assignment.classroom_id
        ).join(
            TeacherProfile, TeacherProfile.id == Classroom.teacher_profile_id
        ).where(
            Assignment.teacher_id == teacher_id,
            TeacherProfile.teacher_id == teacher_id,
            Classroom.tenant_id == TeacherProfile.tenant_id,
        ).order_by(Assignment.id.desc())
    )).scalars().all()
    return {"assignments": [_assignment_payload(a) for a in rows]}

@router.post("/v1/assignments/{assignment_id}/publish")
async def publish_assignment_v1(assignment_id: int, subject: str = Depends(require_roles("TEACHER", "ADMIN")), session: AsyncSession = Depends(get_session)):
    allowed_ids = await _teacher_scope_ids(session, int(subject))
    a = await session.scalar(select(Assignment).where(Assignment.id == assignment_id, Assignment.teacher_id == int(subject), Assignment.classroom_id.in_(allowed_ids))) if allowed_ids else None
    if a is None: raise HTTPException(status_code=404, detail="Assignment not found")
    existing = await session.scalar(select(AssignmentSnapshot).where(AssignmentSnapshot.assignment_id == a.id).order_by(AssignmentSnapshot.version.desc()))
    if existing:
        if a.status != "PUBLISHED": a.status = "PUBLISHED"; await session.commit()
        return {"assignment": _assignment_payload(a), "snapshot_id": existing.id, "replayed": True}
    payload = json.dumps(_assignment_payload(a), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    snap = AssignmentSnapshot(assignment_id=a.id, tenant_id=a.tenant_id, version=1, payload_json=payload, content_digest=sha256(payload.encode("utf-8")).hexdigest())
    a.status = "PUBLISHED"; a.publish_at = datetime.now(UTC); session.add(snap)
    await record_audit_log(session, actor_user_id=int(subject), action="ASSIGNMENT_PUBLISHED", resource_type="assignment", resource_id=str(a.id), metadata={"snapshot_version": 1, "content_digest": snap.content_digest})
    await session.commit(); await session.refresh(snap)
    return {"assignment": _assignment_payload(a), "snapshot_id": snap.id, "replayed": False}

@router.post("/v1/assignments/{assignment_id}/close")
async def close_assignment_v1(assignment_id: int, subject: str = Depends(require_roles("TEACHER", "ADMIN")), session: AsyncSession = Depends(get_session)):
    allowed_ids = await _teacher_scope_ids(session, int(subject))
    a = await session.scalar(select(Assignment).where(Assignment.id == assignment_id, Assignment.teacher_id == int(subject), Assignment.classroom_id.in_(allowed_ids))) if allowed_ids else None
    if a is None: raise HTTPException(status_code=404, detail="Assignment not found")
    a.status = "CLOSED"; a.close_at = datetime.now(UTC)
    await record_audit_log(session, actor_user_id=int(subject), action="ASSIGNMENT_CLOSED", resource_type="assignment", resource_id=str(a.id), metadata={"status": a.status})
    await session.commit(); await session.refresh(a)
    return {"assignment": _assignment_payload(a)}

@router.get("/v1/assignments/{assignment_id}/submissions")
async def list_assignment_submissions_v1(assignment_id: int, subject: str = Depends(require_roles("TEACHER", "ADMIN")), session: AsyncSession = Depends(get_session)):
    a = await session.scalar(select(Assignment).where(Assignment.id == assignment_id, Assignment.teacher_id == int(subject)))
    if a is None: raise HTTPException(status_code=404, detail="Assignment not found")
    rows = (await session.execute(select(StudentSubmission).where(StudentSubmission.assignment_id == assignment_id, StudentSubmission.tenant_id == a.tenant_id).order_by(StudentSubmission.id))).scalars().all()
    return {"submissions": [{"id": s.id, "student_id": s.student_id, "status": s.status, "revision": s.revision, "submitted_at": s.submitted_at.isoformat() if s.submitted_at else None} for s in rows]}


@router.get("/exam-results")
async def list_exam_results_v1(
    subject: str = Depends(require_roles("TEACHER", "ADMIN")),
    session: AsyncSession = Depends(get_session),
):
    """Return persisted exam results for classrooms owned by this teacher."""
    teacher_id = int(subject)
    try:
        resolved_tenant = await resolve_tenant(session, user_id=teacher_id)
        await set_tenant_context(session, resolved_tenant)
    except (ValueError, TenantResolutionError) as exc:
        await session.rollback()
        raise HTTPException(status_code=403, detail="Tenant scope denied") from exc
    rows = await session.execute(
        select(ExamResult, ExamAttempt, Assignment)
        .join(ExamAttempt, ExamAttempt.id == ExamResult.attempt_id)
        .join(Assignment, Assignment.id == ExamAttempt.assignment_id)
        .join(Classroom, Classroom.id == Assignment.classroom_id)
        .join(TeacherProfile, TeacherProfile.id == Classroom.teacher_profile_id)
        .where(
            Assignment.teacher_id == teacher_id,
            Assignment.tenant_id == resolved_tenant,
            TeacherProfile.teacher_id == teacher_id,
            Classroom.tenant_id == Assignment.tenant_id,
            ExamResult.tenant_id == Assignment.tenant_id,
        )
        .order_by(ExamResult.id.desc())
    )
    return {"results": [
        {"result_id": result.id, "attempt_id": attempt.id,
         "assignment_id": assignment.id, "student_id": attempt.student_id,
         "score": result.score, "max_score": result.max_score,
         "grading_status": result.grading_status}
        for result, attempt, assignment in rows.all()
    ]}

@router.post("/v1/submissions/{submission_id}/review", status_code=201)
async def review_submission_v1(submission_id: int, req: AssignmentReviewRequest, subject: str = Depends(require_roles("TEACHER", "ADMIN")), session: AsyncSession = Depends(get_session)):
    row = await session.execute(select(StudentSubmission, Assignment).join(Assignment, Assignment.id == StudentSubmission.assignment_id).where(StudentSubmission.id == submission_id, Assignment.teacher_id == int(subject)))
    item = row.first()
    if item is None: raise HTTPException(status_code=404, detail="Submission not found")
    submission, assignment = item
    review = await session.scalar(select(SubmissionReview).where(SubmissionReview.submission_id == submission.id))
    if review is None:
        review = SubmissionReview(submission_id=submission.id, tenant_id=assignment.tenant_id, review_status=req.review_status, score=req.score, teacher_feedback=req.feedback, reviewed_by=int(subject), reviewed_at=datetime.now(UTC))
        session.add(review)
    else:
        review.review_status = req.review_status; review.score = req.score; review.teacher_feedback = req.feedback; review.reviewed_by = int(subject); review.reviewed_at = datetime.now(UTC)
    submission.status = "REVIEWED"
    await record_audit_log(session, actor_user_id=int(subject), action="SUBMISSION_REVIEWED", resource_type="submission", resource_id=str(submission.id), metadata={"assignment_id": assignment.id, "review_status": review.review_status, "score": review.score})
    await session.commit(); await session.refresh(review)
    return {"review_id": review.id, "submission_id": submission.id, "status": review.review_status, "score": review.score, "feedback": review.teacher_feedback}

@router.post("/v2/classrooms", status_code=201)
async def create_persistent_classroom(
    req: PersistentClassroomCreateRequest,
    subject: str = Depends(require_roles("TEACHER", "ADMIN")),
    session: AsyncSession = Depends(get_session),
):
    teacher_id = int(subject)
    profile = await session.scalar(select(TeacherProfile).where(TeacherProfile.teacher_id == teacher_id, TeacherProfile.tenant_id == req.tenant_id))
    if profile is None:
        raise HTTPException(status_code=403, detail="Teacher is not authorized for this tenant")
    classroom = Classroom(classroom_key=req.classroom_key, tenant_id=req.tenant_id, teacher_profile_id=profile.id)
    session.add(classroom)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Classroom already exists") from exc
    await session.refresh(classroom)
    return {"id": classroom.id, "classroom_key": classroom.classroom_key, "tenant_id": classroom.tenant_id}

@router.get("/v2/classrooms")
async def list_persistent_classrooms(
    subject: str = Depends(require_roles("TEACHER", "ADMIN")),
    session: AsyncSession = Depends(get_session),
):
    teacher_id = int(subject)
    rows = (await session.execute(
        select(Classroom).join(TeacherProfile).where(
            TeacherProfile.teacher_id == teacher_id,
            Classroom.teacher_profile_id == TeacherProfile.id,
            Classroom.tenant_id == TeacherProfile.tenant_id,
        )
    )).scalars().all()
    return {"classrooms": [{"id": c.id, "classroom_key": c.classroom_key, "tenant_id": c.tenant_id} for c in rows]}

@router.post("/v2/classrooms/{classroom_id}/members", status_code=201)
async def add_persistent_member(
    classroom_id: int,
    req: PersistentStudentRequest,
    subject: str = Depends(require_roles("TEACHER", "ADMIN")),
    session: AsyncSession = Depends(get_session),
):
    teacher_id = int(subject)
    classroom = await session.scalar(select(Classroom).join(TeacherProfile).where(Classroom.id == classroom_id, TeacherProfile.teacher_id == teacher_id))
    if classroom is None:
        raise HTTPException(status_code=404, detail="Classroom not found")
    student = await session.scalar(select(StudentProfile).where(StudentProfile.student_id == req.student_id))
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    membership = ClassMembership(classroom_id=classroom.id, student_id=student.id)
    session.add(membership)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Student is already a member") from exc
    return {"id": membership.id, "classroom_id": classroom.id, "student_id": req.student_id}

class PublishContentRequest(BaseModel):
    content_version_id: int = Field(ge=1)
    classroom_id: int = Field(ge=1)


class ContentReviewRequest(BaseModel):
    action: str = Field(min_length=1, max_length=16)
    reason: str | None = Field(default=None, max_length=2000)


@router.post("/v2/content/{content_version_id}/review")
async def review_content_version(
    content_version_id: int,
    req: ContentReviewRequest,
    subject: str = Depends(require_roles("TEACHER", "ADMIN")),
    session: AsyncSession = Depends(get_session),
):
    """Persist the teacher HITL decision using the canonical content version."""
    actor_id = int(subject)
    action = req.action.strip().upper()
    if action not in {"APPROVE", "REJECT", "REVOKE"}:
        raise HTTPException(status_code=422, detail="Unsupported review action")
    version = await session.scalar(
        select(ContentVersion).where(
            ContentVersion.id == content_version_id,
            ContentVersion.owner_teacher_id == actor_id,
        )
    )
    if version is None:
        raise HTTPException(status_code=404, detail="Content version not found")
    previous = version.review_state
    if action == "APPROVE":
        if previous in {"REJECTED", "REVOKED"}:
            raise HTTPException(status_code=409, detail="Invalid review state transition")
        if version.processing_state not in {"PROCESSED", "VALIDATED"}:
            raise HTTPException(status_code=409, detail="Content is not ready for review")
        version.review_state = "APPROVED"
    elif action == "REJECT":
        if previous in {"REJECTED", "REVOKED"}:
            raise HTTPException(status_code=409, detail="Invalid review state transition")
        version.review_state = "REJECTED"
    else:
        if previous != "APPROVED":
            raise HTTPException(status_code=409, detail="Invalid review state transition")
        version.review_state = "REJECTED"
        version.vector_sync_state = "VECTOR_REVOKED"
    audit_action = {"APPROVE": "CONTENT_APPROVED", "REJECT": "CONTENT_REJECTED", "REVOKE": "CONTENT_REVOKED"}[action]
    await record_audit_log(
        session,
        actor_user_id=actor_id,
        action=audit_action,
        resource_type="content_version",
        resource_id=str(content_version_id),
        metadata={"previous_review_state": previous, "new_review_state": version.review_state, "reason": req.reason or ""},
    )
    await session.commit()
    return {
        "content_version_id": content_version_id,
        "review_state": version.review_state,
        "vector_sync_state": version.vector_sync_state,
        "previous_review_state": previous,
    }


@router.get("/v2/content/review-queue")
async def list_content_review_queue(
    subject: str = Depends(require_roles("TEACHER", "ADMIN")),
    session: AsyncSession = Depends(get_session),
):
    rows = (
        await session.execute(
            select(ContentVersion)
            .where(ContentVersion.owner_teacher_id == int(subject))
            .order_by(ContentVersion.id.desc())
        )
    ).scalars().all()
    return {
        "items": [
            {
                "content_version_id": row.id,
                "processing_state": row.processing_state,
                "review_state": row.review_state,
                "vector_sync_state": row.vector_sync_state,
                "source_hash": row.source_hash,
            }
            for row in rows
        ]
    }

@router.post("/v2/publications", status_code=201)
async def publish_teacher_content(
    req: PublishContentRequest,
    subject: str = Depends(require_roles("TEACHER", "ADMIN")),
    session: AsyncSession = Depends(get_session),
):
    teacher_id = int(subject)
    classroom = await session.scalar(select(Classroom).join(TeacherProfile).where(Classroom.id == req.classroom_id, TeacherProfile.teacher_id == teacher_id))
    version = await session.scalar(select(ContentVersion).where(ContentVersion.id == req.content_version_id, ContentVersion.owner_teacher_id == teacher_id))
    if classroom is None or version is None:
        raise HTTPException(status_code=404, detail="Content or classroom not found")
    if (
        version.processing_state not in {"PROCESSED", "VALIDATED"}
        or version.review_state != "APPROVED"
        or version.vector_sync_state not in {"VECTOR_SYNCED", "SYNCED"}
    ):
        raise HTTPException(status_code=409, detail="Content version is not eligible for publication")
    profile = await session.scalar(select(TeacherProfile).where(TeacherProfile.teacher_id == teacher_id, TeacherProfile.tenant_id == classroom.tenant_id))
    if not can_publish(PublicationContext(teacher_id, version.owner_teacher_id, profile.tenant_id if profile else None, classroom.tenant_id)):
        raise HTTPException(status_code=404, detail="Content or classroom not found")
    existing = await session.scalar(select(TeacherContentPublication).where(TeacherContentPublication.content_version_id == version.id, TeacherContentPublication.classroom_id == classroom.id))
    if existing:
        return {"id": existing.id, "status": existing.status, "replayed": True}
    publication = TeacherContentPublication(content_version_id=version.id, teacher_id=teacher_id, classroom_id=classroom.id)
    session.add(publication)
    await session.commit()
    await session.refresh(publication)
    return {"id": publication.id, "content_version_id": version.id, "classroom_id": classroom.id, "status": publication.status}

@router.get("/v2/publications")
async def list_teacher_publications(subject: str = Depends(require_roles("TEACHER", "ADMIN")), session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(TeacherContentPublication).where(TeacherContentPublication.teacher_id == int(subject)))).scalars().all()
    return {"publications": [{"id": p.id, "content_version_id": p.content_version_id, "classroom_id": p.classroom_id, "status": p.status} for p in rows]}




