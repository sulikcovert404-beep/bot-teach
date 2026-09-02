import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.models import IngestionIdempotencyKey, SourceDocument
from app.services.curriculum_pipeline_runtime import SQLAlchemyUnitOfWork
from app.services.curriculum_pipeline_api import CASConflictError, IdempotencyConflictError


@pytest_asyncio.fixture
async def sessions():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as c:
        await c.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest.mark.asyncio
async def test_uow_commit_and_rollback(sessions):
    async with SQLAlchemyUnitOfWork(sessions) as uow:
        uow.session.add(SourceDocument(source_id="math-1", title="ریاضی"))
    async with sessions() as s:
        assert (await s.execute(select(SourceDocument))).scalar_one().title == "ریاضی"
    with pytest.raises(RuntimeError):
        async with SQLAlchemyUnitOfWork(sessions) as uow:
            uow.session.add(SourceDocument(source_id="rolled", title="x"))
            raise RuntimeError("abort")
    async with sessions() as s:
        assert (await s.execute(select(SourceDocument).where(SourceDocument.source_id == "rolled"))).scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_idempotency_replay_and_hash_mismatch(sessions):
    async with SQLAlchemyUnitOfWork(sessions) as uow:
        first = await uow.idempotency.lock_or_get("k", "h1")
        await uow.idempotency.complete("k", "h1", {"ok": True})
        replay = await uow.idempotency.lock_or_get("k", "h1")
        assert replay.id == first.id and replay.status == "COMPLETED"
        with pytest.raises(IdempotencyConflictError):
            await uow.idempotency.lock_or_get("k", "h2")
