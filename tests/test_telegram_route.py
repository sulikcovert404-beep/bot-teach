from fastapi.testclient import TestClient

from app.api.routes.telegram import get_bot_client
from app.core.config import get_settings
from app.main import app


def test_mini_app_config_contract() -> None:
    response = TestClient(app).get("/api/v1/telegram/mini-app/config")
    assert response.status_code == 200
    assert response.json()["auth_endpoint"] == "/api/v1/auth/telegram"


def test_webhook_rejects_missing_secret(monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "telegram_webhook_secret", "secret")
    response = TestClient(app).post("/api/v1/telegram/webhook", json={"update_id": 1})
    assert response.status_code == 401


def test_webhook_accepts_valid_secret(monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "telegram_webhook_secret", "secret")
    monkeypatch.setattr(get_settings(), "telegram_bot_token", "test-token")
    response = TestClient(app).post(
        "/api/v1/telegram/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "secret"},
        json={"update_id": 1},
    )
    assert response.status_code == 200
    assert response.json() == {"accepted": True}


def test_webhook_sends_ack_for_text_update(monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "telegram_webhook_secret", "secret")
    sent: list[tuple[int, str]] = []

    class FakeBot:
        async def send_text(self, chat_id: int, text: str) -> None:
            sent.append((chat_id, text))

    app.dependency_overrides[get_bot_client] = lambda: FakeBot()
    try:
        response = TestClient(app).post(
            "/api/v1/telegram/webhook",
            headers={"X-Telegram-Bot-Api-Secret-Token": "secret"},
            json={"message": {"chat": {"id": 42}, "text": "سلام"}},
        )
        assert response.status_code == 200
        assert sent == [(42, "پیام شما دریافت شد.")]
    finally:
        app.dependency_overrides.pop(get_bot_client, None)
