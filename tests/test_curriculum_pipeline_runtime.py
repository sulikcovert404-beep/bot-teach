import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.models import SourceDocument
from app.services.curriculum_pipeline_adapters import (
    IdempotencyRepository,
    UnitOfWork,
)
from app.services.curriculum_pipeline_api import (
    IdempotencyConflictError,
    IdempotencyRecordMissingError,
    SessionNotInitializedError,
)
from app.services.curriculum_pipeline_runtime import SQLAlchemyIdempotency, SQLAlchemyUnitOfWork


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
        assert (
            await s.execute(
                select(SourceDocument).where(SourceDocument.source_id == "rolled")
            )
        ).scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_idempotency_replay_and_hash_mismatch(sessions):
    async with SQLAlchemyUnitOfWork(sessions) as uow:
        first = await uow.idempotency.lock_or_get("k", "h1")
        await uow.idempotency.complete("k", "h1", {"ok": True})
        replay = await uow.idempotency.lock_or_get("k", "h1")
        assert replay.id == first.id and replay.status == "COMPLETED"
        with pytest.raises(IdempotencyConflictError):
            await uow.idempotency.lock_or_get("k", "h2")


@pytest.mark.asyncio
async def test_idempotency_missing_record_fails_closed(sessions):
    async with sessions() as session:
        with pytest.raises(IdempotencyRecordMissingError):
            await SQLAlchemyIdempotency(session).complete("missing", "hash", {"ok": True})


def test_runtime_adapters_conform_to_protocols() -> None:
    _: type[UnitOfWork] = SQLAlchemyUnitOfWork
    _: type[IdempotencyRepository] = SQLAlchemyIdempotency


@pytest.mark.asyncio
async def test_commit_without_session_raises_typed_error(sessions):
    uow = SQLAlchemyUnitOfWork(sessions)
    with pytest.raises(SessionNotInitializedError):
        await uow.commit()


@pytest.mark.asyncio
async def test_uow_cleanup_failure_does_not_mask_primary_exception():
    class FailingSession:
        async def rollback(self) -> None:
            raise RuntimeError("rollback failed")

        async def close(self) -> None:
            raise RuntimeError("close failed")

    uow = SQLAlchemyUnitOfWork(lambda: FailingSession())
    uow.session = FailingSession()
    result = await uow.__aexit__(ValueError, ValueError("primary"), None)
    assert result is None
    assert uow.session is None
