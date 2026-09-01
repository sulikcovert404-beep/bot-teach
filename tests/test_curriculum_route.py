import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.routes.auth import get_session
from app.db.base import Base
from app.db.models import Book, Chapter, Lesson
from app.main import app


@pytest.mark.asyncio
async def test_list_books_returns_nested_curriculum() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    async with sessions() as session:
        book = Book(title="ریاضی", grade="هفتم", subject="ریاضی")
        chapter = Chapter(title="اعداد", position=1)
        chapter.lessons.append(Lesson(title="عددهای صحیح", position=1))
        book.chapters.append(chapter)
        session.add(book)
        await session.commit()

    async def override_session():
        async with sessions() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/curriculum/books")
        assert response.status_code == 200
        assert response.json()[0]["chapters"][0]["lessons"][0]["title"] == "عددهای صحیح"
    finally:
        app.dependency_overrides.pop(get_session, None)
        await engine.dispose()


def test_curriculum_write_routes_require_role_authentication() -> None:
    from fastapi.testclient import TestClient

    client = TestClient(app)
    response = client.post("/api/v1/curriculum/books", json={"title": "ریاضی"})
    assert response.status_code == 401
