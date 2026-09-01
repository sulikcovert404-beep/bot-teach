
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.routes.auth import get_session
from app.core.config import get_settings
from app.db.base import Base
from app.main import app
from app.security.tokens import create_access_token


def test_record_event_and_get_adaptive_recommendation(monkeypatch) -> None:
    import asyncio

    async def run() -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        sessions = async_sessionmaker(engine, expire_on_commit=False)

        async def override_session():
            async with sessions() as session:
                yield session

        settings = get_settings()
        monkeypatch.setattr(settings, "jwt_secret", "x" * 32)
        app.dependency_overrides[get_session] = override_session
        token = create_access_token("7", settings.jwt_secret, role="STUDENT")
        headers = {"Authorization": f"Bearer {token}"}
        try:
            with TestClient(app) as client:
                event = client.post(
                    "/api/v1/analytics/events",
                    headers=headers,
                    json={"event_type": "quiz", "duration_seconds": 120, "score": 0.95},
                )
                assert event.status_code == 201
                recommendation = client.get("/api/v1/analytics/recommendation", headers=headers)
                assert recommendation.status_code == 200
                assert recommendation.json()["level"] == "CHALLENGE"
        finally:
            app.dependency_overrides.pop(get_session, None)
            await engine.dispose()

    asyncio.run(run())


def test_learning_event_rejects_blank_event_type() -> None:
    response = TestClient(app).post(
        "/api/v1/analytics/events", json={"event_type": "   "}
    )
    assert response.status_code == 401
