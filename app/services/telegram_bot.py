import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class TelegramAPIError(RuntimeError):
    """A safe, structured Telegram API failure without request secrets."""

    def __init__(
        self,
        *,
        http_status: int,
        error_code: int | None,
        description: str | None,
        destination_type: str,
    ) -> None:
        self.http_status = http_status
        self.error_code = error_code
        self.description = description
        self.destination_type = destination_type
        super().__init__(f"Telegram API rejected message ({http_status})")


class TelegramBotClient:
    def __init__(self, bot_token: str, *, timeout_seconds: float = 10.0) -> None:
        if not bot_token:
            raise ValueError("Telegram bot token is required")
        self._base_url = f"https://api.telegram.org/bot{bot_token}"
        self._url = f"{self._base_url}/sendMessage"
        self._timeout = timeout_seconds

    async def send_text(
        self, chat_id: int, text: str, *, reply_markup: dict[str, object] | None = None
    ) -> None:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            payload: dict[str, object] = {"chat_id": chat_id, "text": text}
            if reply_markup is not None:
                payload["reply_markup"] = reply_markup
            response = await client.post(self._url, json=payload)
            try:
                payload: dict[str, Any] = response.json()
            except ValueError:
                payload = {}
            if response.is_error or payload.get("ok") is not True:
                error = TelegramAPIError(
                    http_status=response.status_code,
                    error_code=payload.get("error_code") if isinstance(payload.get("error_code"), int) else None,
                    description=payload.get("description") if isinstance(payload.get("description"), str) else None,
                    destination_type=("private" if chat_id >= 0 else "group_or_channel"),
                )
                logger.warning(
                    "telegram_send_failed status=%s error_code=%s description=%s destination_type=%s exception_class=%s",
                    error.http_status,
                    error.error_code,
                    error.description,
                    error.destination_type,
                    type(error).__name__,
                )
                raise error
    async def send_audio(self, chat_id: int, audio: str, *, caption: str | None = None) -> None:
        await self._send_media("sendAudio", chat_id, "audio", audio, caption)

    async def send_document(self, chat_id: int, document: str, *, caption: str | None = None) -> None:
        await self._send_media("sendDocument", chat_id, "document", document, caption)

    async def _send_media(self, method: str, chat_id: int, field: str, value: str, caption: str | None) -> None:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            payload: dict[str, object] = {"chat_id": chat_id, field: value}
            if caption:
                payload["caption"] = caption
            response = await client.post(f"{self._base_url}/{method}", json=payload)
            try:
                body: dict[str, Any] = response.json()
            except ValueError:
                body = {}
            if response.is_error or body.get("ok") is not True:
                raise TelegramAPIError(http_status=response.status_code, error_code=body.get("error_code") if isinstance(body.get("error_code"), int) else None, description=body.get("description") if isinstance(body.get("description"), str) else None, destination_type=("private" if chat_id >= 0 else "group_or_channel"))

