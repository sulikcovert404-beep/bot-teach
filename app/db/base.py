from collections.abc import AsyncGenerator
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


@lru_cache(maxsize=8)
def build_session_factory(database_url: str) -> async_sessionmaker[AsyncSession]:
    if not database_url:
        raise ValueError("DATABASE_URL is required to create a database session")
    engine = create_async_engine(database_url, pool_pre_ping=True)
    return async_sessionmaker(engine, expire_on_commit=False)


async def dispose_session_factory(factory: async_sessionmaker[AsyncSession]) -> None:
    bind = factory.kw.get("bind")
    if bind is not None and hasattr(bind, "dispose"):
        await bind.dispose()


async def session_dependency(
    factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    async with factory() as session:
        yield session
