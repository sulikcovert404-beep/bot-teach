import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.api.routes.auth import get_session
from app.api.routes.telegram import (
    callback_reply,
    get_bot_client,
    is_navigation_label,
    navigation_payload,
    reply_for_text,
)
from app.core.config import get_settings
from app.main import create_app

app = create_app()
from app.services.telegram_bot import TelegramAPIError


@pytest.fixture(autouse=True)
def telegram_webhook_session_override():
    """Keep webhook contract tests offline while satisfying the route dependency."""

    class TestSession:
        def add(self, _object) -> None:
            return None

        async def flush(self) -> None:
            return None

        async def rollback(self) -> None:
            return None

        async def commit(self) -> None:
            return None

    async def override_session():
        yield TestSession()

    app.dependency_overrides[get_session] = override_session
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_session, None)


def test_mini_app_config_contract() -> None:
    response = TestClient(app).get("/api/v1/telegram/mini-app/config")
    assert response.status_code == 200
    assert response.json()["auth_endpoint"] == "/api/v1/auth/telegram"


def test_telegram_basic_commands_have_dedicated_replies() -> None:
    assert "خوش آمدید" in reply_for_text("/start")
    assert "راهنما" in reply_for_text("/help extra")
    assert reply_for_text("سلام") == "پیام شما دریافت شد."


def test_reply_keyboard_labels_are_navigation_intents() -> None:
    label = "🏫 کلاس‌های من"
    assert is_navigation_label(label)
    assert "مینی‌اپ" in reply_for_text(label)
    assert not is_navigation_label("یک سؤال آموزشی")


def test_navigation_payload_is_built_without_sending() -> None:
    payload = navigation_payload(web_app_url="https://codeshow.ir/mini-app")
    assert "reply_markup" in payload
    assert "inline_markup" in payload
    assert payload["inline_markup"]["inline_keyboard"][0][0]["web_app"]["url"] == "https://codeshow.ir/mini-app"


def test_unknown_callback_uses_safe_fallback() -> None:
    assert callback_reply("open:unknown") is not None
    assert callback_reply("open:tutor") is None


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


def test_webhook_maps_telegram_provider_failure(monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "telegram_webhook_secret", "secret")

    class FailingBot:
        async def send_text(self, chat_id: int, text: str) -> None:
            raise RuntimeError("provider down")

    app.dependency_overrides[get_bot_client] = lambda: FailingBot()
    try:
        response = TestClient(app).post(
            "/api/v1/telegram/webhook",
            headers={"X-Telegram-Bot-Api-Secret-Token": "secret"},
            json={"message": {"chat": {"id": 42}, "text": "سلام"}},
        )
        assert response.status_code == 502
    finally:
        app.dependency_overrides.pop(get_bot_client, None)


def test_webhook_maps_structured_telegram_api_failure(monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "telegram_webhook_secret", "secret")

    class FailingBot:
        async def send_text(self, chat_id: int, text: str) -> None:
            raise TelegramAPIError(
                http_status=403,
                error_code=403,
                description="Forbidden",
                destination_type="private",
            )

    app.dependency_overrides[get_bot_client] = lambda: FailingBot()
    try:
        response = TestClient(app).post(
            "/api/v1/telegram/webhook",
            headers={"X-Telegram-Bot-Api-Secret-Token": "secret"},
            json={"message": {"chat": {"id": 42}, "text": "سلام"}},
        )
        # Permanent Telegram 4xx errors are acknowledged to prevent webhook poisoning.
        assert response.status_code == 200
    finally:
        app.dependency_overrides.pop(get_bot_client, None)


def test_webhook_ignores_duplicate_update(monkeypatch) -> None:
    monkeypatch.setattr(get_settings(), "telegram_webhook_secret", "secret")
    sent: list[tuple[int, str]] = []

    class FakeBot:
        async def send_text(self, chat_id: int, text: str) -> None:
            sent.append((chat_id, text))

    class DuplicateSession:
        def add(self, _object) -> None:
            return None

        async def flush(self) -> None:
            raise IntegrityError("duplicate", {}, RuntimeError("unique constraint"))

        async def rollback(self) -> None:
            return None

    app.dependency_overrides[get_bot_client] = lambda: FakeBot()
    app.dependency_overrides[get_session] = lambda: DuplicateSession()
    try:
        response = TestClient(app).post(
            "/api/v1/telegram/webhook",
            headers={"X-Telegram-Bot-Api-Secret-Token": "secret"},
            json={"update_id": 99, "message": {"chat": {"id": 42}, "text": "سلام"}},
        )
        assert response.status_code == 200
        assert response.json() == {"accepted": True}
        assert sent == []
    finally:
        app.dependency_overrides.pop(get_bot_client, None)
        app.dependency_overrides.pop(get_session, None)
import pytest

from app.services.telegram_delivery import build_delivery, validate_asset_access


def test_delivery_methods():
    assert build_delivery(asset_type="PODCAST", chat_id=1, content="audio-id", caption="c").method == "sendAudio"
    assert build_delivery(asset_type="PDF", chat_id=1, content="doc-id", caption="c").method == "sendDocument"
    mcq = build_delivery(asset_type="MCQ", chat_id=1, content="q", caption="c")
    assert mcq.method == "sendMessage"
    assert "caption" not in mcq.payload

def test_delivery_access_is_fail_closed():
    validate_asset_access(review_state="APPROVED", tenant_id=1, requested_tenant_id=1, lesson_id=2, requested_lesson_id=2)
    for kwargs in ({"review_state":"PENDING","tenant_id":1,"requested_tenant_id":1,"lesson_id":2,"requested_lesson_id":2},{"review_state":"APPROVED","tenant_id":1,"requested_tenant_id":2,"lesson_id":2,"requested_lesson_id":2},{"review_state":"APPROVED","tenant_id":1,"requested_tenant_id":1,"lesson_id":2,"requested_lesson_id":3}):
        with pytest.raises(PermissionError): validate_asset_access(**kwargs)
