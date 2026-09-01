from typing import Any

import httpx


class TelegramBotClient:
    def __init__(self, bot_token: str, *, timeout_seconds: float = 10.0) -> None:
        if not bot_token:
            raise ValueError("Telegram bot token is required")
        self._url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        self._timeout = timeout_seconds

    async def send_text(self, chat_id: int, text: str) -> None:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(self._url, json={"chat_id": chat_id, "text": text})
            response.raise_for_status()
            payload: dict[str, Any] = response.json()
            if payload.get("ok") is not True:
                raise RuntimeError("Telegram Bot API rejected the message")
