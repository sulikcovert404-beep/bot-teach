import httpx
import pytest

from app.services.telegram_bot import TelegramAPIError, TelegramBotClient


@pytest.mark.asyncio
async def test_bot_client_sends_text(monkeypatch) -> None:
    captured: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = request.content
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)

    class Client(TelegramBotClient):
        async def send_text(self, chat_id: int, text: str) -> None:
            async with httpx.AsyncClient(transport=transport) as client:
                response = await client.post(self._url, json={"chat_id": chat_id, "text": text})
                response.raise_for_status()
                assert response.json()["ok"] is True

    await Client("token").send_text(42, "سلام")
    assert captured["url"] == "https://api.telegram.org/bottoken/sendMessage"
    assert b'"chat_id":42' in captured["body"]  # type: ignore[operator]


@pytest.mark.asyncio
async def test_bot_client_exposes_redacted_api_error(monkeypatch) -> None:
    class FakeClient:
        def __init__(self, **_kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args) -> None:
            return None

        async def post(self, _url: str, *, json: dict[str, object]) -> httpx.Response:
            assert json["chat_id"] == 42
            return httpx.Response(403, json={"ok": False, "error_code": 403, "description": "Forbidden"})

    monkeypatch.setattr("app.services.telegram_bot.httpx.AsyncClient", FakeClient)

    with pytest.raises(TelegramAPIError) as exc_info:
        await TelegramBotClient("token").send_text(42, "سلام")
    assert exc_info.value.http_status == 403
    assert exc_info.value.error_code == 403
    assert exc_info.value.description == "Forbidden"
    assert "token" not in str(exc_info.value)
    assert "سلام" not in str(exc_info.value)
