import pytest
import pytest_asyncio
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.models import ContentVersion, SourceDocument, TransactionalOutboxEvent
from app.services.pipeline_transactions import (
    ConflictError,
    InvalidStateError,
    publish_content_version,
)


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as value:
        yield value
    await engine.dispose()


async def seed(session):
    document = SourceDocument(source_id="src-1", title="درس", uri=None)
    session.add(document)
    await session.flush()
    version = ContentVersion(
        source_document_id=document.id,
        version_number=1,
        processing_state="VALIDATED",
        review_state="APPROVED",
        vector_sync_state="VECTOR_SYNCED",
        pipeline_digest="digest-۱",
    )
    session.add(version)
    await session.commit()
    return version.id


@pytest.mark.asyncio
async def test_publish_is_atomic_and_replay_safe(session):
    version_id = await seed(session)
    first = await publish_content_version(
        session,
        content_version_id=version_id,
        expected_pointer_version=None,
        idempotency_key="idem-1",
        request_hash="request-1",
        event_id="event-1",
    )
    replay = await publish_content_version(
        session,
        content_version_id=version_id,
        expected_pointer_version=1,
        idempotency_key="idem-1",
        request_hash="request-1",
        event_id="event-ignored",
    )
    assert first.replayed is False
    assert replay.replayed is True
    events = (await session.scalars(select(TransactionalOutboxEvent))).all()
    assert len(events) == 1


@pytest.mark.asyncio
async def test_cas_conflict_rolls_back(session):
    version_id = await seed(session)
    await publish_content_version(
        session,
        content_version_id=version_id,
        expected_pointer_version=None,
        idempotency_key="idem-1",
        request_hash="request-1",
        event_id="event-1",
    )
    with pytest.raises(ConflictError):
        await publish_content_version(
            session,
            content_version_id=version_id,
            expected_pointer_version=99,
            idempotency_key="idem-2",
            request_hash="request-2",
            event_id="event-2",
        )


@pytest.mark.asyncio
async def test_invalid_gate_does_not_persist(session):
    version_id = await seed(session)
    await session.execute(update(ContentVersion).where(ContentVersion.id == version_id).values(vector_sync_state="VECTOR_PENDING"))
    await session.commit()
    with pytest.raises(InvalidStateError):
        await publish_content_version(
            session,
            content_version_id=version_id,
            expected_pointer_version=None,
            idempotency_key="idem-1",
            request_hash="request-1",
            event_id="event-1",
        )
