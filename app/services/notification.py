from __future__ import annotations

from app.core.channels import Channel, NotificationService
from app.services.telegram_bot import TelegramBotClient


class TelegramNotificationProvider:
    channel = Channel.TELEGRAM

    def __init__(self, client: TelegramBotClient) -> None:
        self._client = client

    async def send(self, destination: str, message: str, *, notification_id: str, metadata=None) -> None:
        if metadata and metadata.get("reply_markup") is not None:
            await self._client.send_text(int(destination), message, reply_markup=metadata["reply_markup"])
        else:
            await self._client.send_text(int(destination), message)


def telegram_notifications(client: TelegramBotClient) -> NotificationService:
    return NotificationService([TelegramNotificationProvider(client)])
