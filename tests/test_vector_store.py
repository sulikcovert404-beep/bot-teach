import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.services.vector_store import PgVectorStore, VectorSearchRequest


@pytest.mark.asyncio
async def test_pgvector_store_requires_postgresql() -> None:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        store = PgVectorStore(session)
        with pytest.raises(RuntimeError, match="PostgreSQL"):
            await store.search(VectorSearchRequest([0.1, 0.2]))
    await engine.dispose()


@pytest.mark.asyncio
async def test_pgvector_store_rejects_invalid_embedding_before_database_call() -> None:
    engine = create_async_engine("sqlite+aiosqlite://")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        store = PgVectorStore(session)
        with pytest.raises(RuntimeError, match="PostgreSQL"):
            await store.upsert_embedding(chunk_id=1, embedding=[0.1], embedding_model="model")
    await engine.dispose()
