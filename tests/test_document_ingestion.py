import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.services.document_ingestion import DatabaseRetriever, ingest_document, split_text


@pytest.mark.asyncio
async def test_ingest_and_retrieve_source_chunks() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        result = await ingest_document(
            session,
            source_id="book-1",
            title="علوم",
            text="سلول واحد بنیادی زندگی است.\nگیاهان فتوسنتز می‌کنند.",
            chunk_size=40,
        )
        await session.commit()
        assert result.chunk_count == 2
        chunks = await DatabaseRetriever(session).retrieve("فتوسنتز")
        assert len(chunks) == 1
        assert chunks[0].source_id == "book-1"
    await engine.dispose()


def test_split_text_rejects_invalid_input() -> None:
    with pytest.raises(ValueError):
        split_text("", chunk_size=10)
    with pytest.raises(ValueError):
        split_text("text", chunk_size=0)
