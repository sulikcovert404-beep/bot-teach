import hashlib
import hmac
import json
import time
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.routes.auth import get_session
from app.core.config import get_settings
from app.db.base import Base
from app.db.models import Subscription
from app.main import app


def signed_init_data(token: str, auth_date: int) -> str:
    user = json.dumps({"id": 987, "username": "e2e_student"}, separators=(",", ":"))
    check_string = f"auth_date={auth_date}\nuser={user}"
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    signature = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    return f"auth_date={auth_date}&user={quote(user)}&hash={signature}"


@pytest.mark.asyncio
async def test_telegram_auth_then_subscription_read(monkeypatch) -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    async def override_session():
        async with sessions() as session:
            yield session

    settings = get_settings()
    monkeypatch.setattr(settings, "database_url", "sqlite+aiosqlite://")
    monkeypatch.setattr(settings, "telegram_bot_token", "e2e-token")
    monkeypatch.setattr(settings, "jwt_secret", "x" * 32)
    app.dependency_overrides[get_session] = override_session
    try:
        with TestClient(app) as client:
            auth = client.post(
                "/api/v1/auth/telegram",
                json={"init_data": signed_init_data("e2e-token", int(time.time()))},
            )
            assert auth.status_code == 200
            token = auth.json()["access_token"]
            async with sessions() as session:
                session.add(Subscription(user_id=auth.json()["user_id"], plan="STUDENT_PLUS"))
                await session.commit()
            subscription = client.get(
                "/api/v1/subscription", headers={"Authorization": f"Bearer {token}"}
            )
            assert subscription.status_code == 200
            assert subscription.json()["plan"] == "STUDENT_PLUS"
    finally:
        app.dependency_overrides.pop(get_session, None)
        await engine.dispose()
