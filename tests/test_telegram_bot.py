import httpx
import pytest

from app.services.telegram_bot import TelegramBotClient


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
