import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.services.usage_repository import record_usage


@pytest.mark.asyncio
async def test_record_usage_persists_event() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        event = await record_usage(
            session,
            user_id=1,
            task_type="tutor",
            model="test-model",
            requested_tokens=100,
            charged_tokens=80,
        )
        assert event.id is not None
    await engine.dispose()

