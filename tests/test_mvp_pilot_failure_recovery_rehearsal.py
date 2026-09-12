"""Disposable failure/recovery rehearsal for the MVP pilot gates."""

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.db.base import Base
from app.db.models import ContentGenerationJob, GenerationAttempt
from app.security.dependencies import authorize_role, require_user
from app.services.content_generation import GenerationService


@pytest.mark.asyncio
async def test_ai_generation_failure_retries_then_reaches_terminal_state() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        service = GenerationService()
        job = await service.create_or_reuse_job(session, content_version_id=7001, asset_type="SUMMARY", generation_parameters={"fixture": True})
        await service.retry_or_fail(session, job, "PROVIDER_TIMEOUT", max_attempts=2)
        assert job.status == "PENDING"
        job.attempt_count = 2
        await service.retry_or_fail(session, job, "PROVIDER_TIMEOUT", max_attempts=2)
        await session.commit()
        assert job.status == "FAILED"
        attempts = (await session.scalars(select(GenerationAttempt).where(GenerationAttempt.job_id == job.id))).all()
        assert len(attempts) == 2
    await engine.dispose()


def test_authorization_failure_is_denied_without_state_change(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "jwt_secret", "x" * 32)
    with pytest.raises(HTTPException) as missing:
        require_user(None)
    assert missing.value.status_code == 401
    with pytest.raises(HTTPException) as forbidden:
        authorize_role("STUDENT", {"TEACHER"})
    assert forbidden.value.status_code == 403


def test_delivery_content_failure_validation_rejects_bad_webapp_signature() -> None:
    from app.adapters.telegram import validate_web_app_init_data

    with pytest.raises(ValueError, match="signature"):
        validate_web_app_init_data("auth_date=1&user=%7B%7D&hash=bad", "fixture-token", now=2)
