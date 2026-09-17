import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.services.content_generation import GenerationService


@pytest.mark.asyncio
async def test_mock_generation_and_idempotency():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        service = GenerationService()
        job = await service.create_or_reuse_job(session, content_version_id=1, asset_type="SUMMARY", generation_parameters={"v": 1})
        claimed = await service.claim_next(session)
        assert claimed is not None and claimed.id == job.id
        job.status = "PENDING"
        reused = await service.create_or_reuse_job(session, content_version_id=1, asset_type="SUMMARY", generation_parameters={"v": 1})
        assert reused.id == job.id
        asset = await service.run_mock(session, job, "متن آموزشی")
        assert job.status == "COMPLETED"
        assert asset.review_state == "DRAFT"
        assert asset.content_hash
        await service.retry_or_fail(session, job, "PROVIDER_TIMEOUT", max_attempts=3)
        assert job.status == "PENDING"
        job.attempt_count = 3
        await service.retry_or_fail(session, job, "PROVIDER_TIMEOUT", max_attempts=3)
        assert job.status == "FAILED"
    await engine.dispose()
