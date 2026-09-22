import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.routes.student import get_student_progress
from app.api.routes.tutor import TutorRequest, tutor_answer
from app.db.base import Base
from app.db.models import (
    AIUsageEvent,
    BetaQualityAudit,
    StudentProfile,
    User,
)


class _EmptyResult:
    def scalar_one_or_none(self):
        return None


class _ContextSession:
    async def execute(self, _statement):
        return _EmptyResult()


@pytest.mark.asyncio
async def test_tutor_context_fails_closed_for_partial_and_foreign_context():
    session = _ContextSession()
    with pytest.raises(HTTPException) as partial:
        await tutor_answer(TutorRequest(query="q", classroom_id=1), subject="42", session=session)
    assert partial.value.status_code == 422

    with pytest.raises(HTTPException) as foreign:
        await tutor_answer(
            TutorRequest(query="q", school_id="other", classroom_id=1, assignment_id=2),
            subject="42",
            session=session,
        )
    assert foreign.value.status_code == 403


@pytest.mark.asyncio
async def test_progress_read_model_empty_state_and_tutor_provenance():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    try:
        async with sessions() as session:
            session.add_all([User(id=1, username="student", role="STUDENT"), StudentProfile(student_id=1)])
            await session.commit()
            empty = await get_student_progress(subject="1", session=session)
            assert empty["progress_provenance"]["empty_state"] is True
            assert empty["progress_provenance"]["tutor_interaction_count"] == 0

            session.add(
                BetaQualityAudit(
                    user_id=1,
                    query="ریاضی",
                    model="test",
                    has_citations=True,
                    latency_ms=1,
                    tokens_used=1,
                    is_success=True,
                )
            )
            session.add(
                AIUsageEvent(
                    user_id=1,
                    task_type="ai_tutor",
                    model="test",
                    requested_tokens=1,
                    charged_tokens=1,
                )
            )
            await session.commit()
            populated = await get_student_progress(subject="1", session=session)
            provenance = populated["progress_provenance"]
            assert provenance["empty_state"] is False
            assert provenance["tutor_interaction_count"] == 1
            assert "AIUsageEvent" in provenance["source"]
    finally:
        await engine.dispose()
