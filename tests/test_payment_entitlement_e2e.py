import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.routes.auth import get_session
from app.core.config import get_settings
from app.db.base import Base
from app.main import app
from app.security.tokens import create_access_token


@pytest.mark.asyncio
async def test_payment_to_entitlement_end_to_end(monkeypatch) -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    async def override_session():
        async with sessions() as session:
            yield session

    settings = get_settings()
    monkeypatch.setattr(settings, "jwt_secret", "x" * 32)
    monkeypatch.setattr(settings, "payment_webhook_secret", "payment-secret")
    app.dependency_overrides[get_session] = override_session
    token = create_access_token("7", settings.jwt_secret, role="STUDENT")
    headers = {"Authorization": f"Bearer {token}"}
    try:
        with TestClient(app) as client:
            intent = client.post(
                "/api/v1/payments/intent",
                headers=headers,
                json={"provider": "test", "amount": 250000, "plan": "STUDENT_PLUS"},
            )
            assert intent.status_code == 200
            transaction_id = intent.json()["provider_transaction_id"]
            callback = client.post(
                "/api/v1/payments/webhook",
                headers={"X-Payment-Webhook-Secret": "payment-secret"},
                json={
                    "provider_transaction_id": transaction_id,
                    "status": "SUCCEEDED",
                    "plan": "STUDENT_PLUS",
                },
            )
            assert callback.status_code == 200
            subscription = client.get("/api/v1/subscription", headers=headers)
            assert subscription.status_code == 200
            assert subscription.json()["plan"] == "STUDENT_PLUS"
            assert "SMART_SUMMARY" in subscription.json()["features"]
    finally:
        app.dependency_overrides.pop(get_session, None)
        await engine.dispose()
