from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.auth import get_session
from app.core.config import get_settings
from app.domain.entitlements.models import FeatureCode
from app.security.entitlements import require_feature_access
from app.services.ai_gateway import (
    GeminiProvider,
    ModelRouter,
    StructuredLoggingAIProviderObserver,
)
from app.services.ai_tutor import AITutor
from app.services.cohort_feedback import (
    FeedbackSubmitRequest,
    record_beta_quality_audit,
    record_user_feedback,
)
from app.services.document_ingestion import DatabaseRetriever
from app.services.usage_repository import record_usage

router = APIRouter(prefix="/tutor", tags=["ai-tutor"])


class TutorRequest(BaseModel):
    query: str = Field(min_length=1, max_length=10_000)
    max_tokens: int = Field(default=1_200, ge=1, le=4_000)


class TutorResponse(BaseModel):
    text: str
    model: str
    task_type: str = "ai_tutor"
    # Optional V2 fields keep existing consumers compatible while making the
    # backend authority and citation boundary explicit for new clients.
    citations: list[dict[str, object]] = Field(default_factory=list)
    access: dict[str, object] = Field(default_factory=lambda: {"decision": "ALLOW", "upgrade_required": False})
    usage: dict[str, object] = Field(default_factory=dict)


@router.post("/answer", response_model=TutorResponse)
async def tutor_answer(
    request: TutorRequest,
    subject: str = Depends(require_feature_access(FeatureCode.BOOK_QA)),
    session: AsyncSession = Depends(get_session),
) -> TutorResponse:
    try:
        user_id = int(subject)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user identity"
        ) from exc

    from app.services.safety_limits import check_beta_safety_limits
    await check_beta_safety_limits(session, user_id=user_id, query=request.query)

    import time
    start_t = time.perf_counter()

    settings = get_settings()
    if not settings.gemini_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI provider unavailable"
        )
    try:
        result = await AITutor(
            GeminiProvider(
                settings.gemini_api_key,
                observer=StructuredLoggingAIProviderObserver(),
            ),
            ModelRouter(settings.ai_default_model),
            DatabaseRetriever(session),
        ).answer(request.query, max_tokens=request.max_tokens)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI provider unavailable"
        ) from exc

    latency_ms = int((time.perf_counter() - start_t) * 1000)
    charged_tokens = (
        min(result.usage_tokens, request.max_tokens)
        if result.usage_tokens is not None
        else request.max_tokens
    )

    await record_usage(
        session,
        user_id=user_id,
        task_type="ai_tutor",
        model=result.model,
        requested_tokens=request.max_tokens,
        charged_tokens=charged_tokens,
    )

    from app.services.cohort_feedback import (
        FeedbackSubmitRequest,
        record_beta_quality_audit,
        record_user_feedback,
    )
    await record_beta_quality_audit(
        session,
        user_id=user_id,
        query=request.query,
        model=result.model,
        answer_text=result.text,
        latency_ms=latency_ms,
        tokens_used=charged_tokens,
        is_success=True,
    )

    await session.commit()
    return TutorResponse(
        text=result.text,
        model=result.model,
        citations=[
            {
                "source_id": citation.source_id,
                "chunk_id": citation.chunk_id,
                "page": citation.page,
                "chapter": citation.chapter,
                "lesson": citation.lesson,
            }
            for citation in result.citations
            if hasattr(citation, "source_id")
        ],
        access={"decision": "ALLOW", "upgrade_required": False},
        usage={"quota_consumed": charged_tokens},
    )


@router.post("/feedback")
async def submit_feedback(
    request: FeedbackSubmitRequest,
    subject: str = Depends(require_feature_access(FeatureCode.BOOK_QA)),
    session: AsyncSession = Depends(get_session),
):
    try:
        user_id = int(subject)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user identity"
        ) from exc

    from app.services.cohort_feedback import record_user_feedback
    fb = await record_user_feedback(session, user_id=user_id, req=request)
    return {"status": "success", "feedback_id": fb.id, "rating": fb.rating}


@router.get("/history")
async def get_student_history(
    subject: str = Depends(require_feature_access(FeatureCode.BOOK_QA)),
    session: AsyncSession = Depends(get_session),
):
    try:
        user_id = int(subject)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user identity"
        ) from exc

    from sqlalchemy import desc, select

    from app.db.models import BetaQualityAudit

    audits = (
        await session.execute(
            select(BetaQualityAudit)
            .where(BetaQualityAudit.user_id == user_id)
            .order_by(desc(BetaQualityAudit.id))
            .limit(10)
        )
    ).scalars().all()

    history_items = [
        {
            "id": a.id,
            "query": a.query,
            "has_citations": a.has_citations,
            "latency_ms": a.latency_ms,
            "created_at": a.created_at.isoformat(),
        }
        for a in audits
    ]

    # Calculate personalized recommended next topic
    recommendation = "فیزیک دهم — فصل ۳: کار و انرژی جنبشی"
    if any("نیوتن" in a.query for a in audits):
        recommendation = "ریاضیات دهم — معادله درجه دوم و بررسی ریشه‌ها با دلتا"
    elif any("دلتا" in a.query for a in audits):
        recommendation = "زیست‌شناسی دهم — غشای یاخته و انتقال فعال"

    return {
        "user_id": user_id,
        "total_queries": len(history_items),
        "history": history_items,
        "learning_path": {
            "current_mastery_level": "متوسط (پایه دهم و یازدهم)",
            "recommended_next_topic": recommendation,
            "suggested_review": "مرور مباحث دارای استناد کتب درسی",
        },
    }
