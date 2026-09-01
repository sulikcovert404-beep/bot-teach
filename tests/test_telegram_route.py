from fastapi.testclient import TestClient

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
    response = TestClient(app).post(
        "/api/v1/telegram/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "secret"},
        json={"update_id": 1},
    )
    assert response.status_code == 200
    assert response.json() == {"accepted": True}
