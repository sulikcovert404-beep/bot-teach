import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.services.audit_repository import record_audit_log


@pytest.mark.asyncio
async def test_audit_repository_rejects_sensitive_metadata() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        with pytest.raises(ValueError, match="Sensitive"):
            await record_audit_log(
                session,
                actor_user_id=None,
                action="login",
                resource_type="user",
                resource_id="1",
                metadata={"api_token": "hidden"},
            )
    await engine.dispose()
