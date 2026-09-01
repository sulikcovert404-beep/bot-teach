import hmac
from typing import Any

from fastapi import APIRouter, Body, Depends, Header, HTTPException, status
from pydantic import BaseModel

from app.core.config import get_settings
from app.services.telegram_bot import TelegramBotClient

router = APIRouter(prefix="/telegram", tags=["telegram"])


class TelegramWebhookResponse(BaseModel):
    accepted: bool = True


class MiniAppConfigResponse(BaseModel):
    api_version: str = "v1"
    platform: str = "telegram-mini-app"
    auth_endpoint: str = "/api/v1/auth/telegram"


def get_bot_client() -> TelegramBotClient | None:
    token = get_settings().telegram_bot_token
    return TelegramBotClient(token) if token else None


def reply_for_text(text: str | None) -> str:
    command = (text or "").strip().split(maxsplit=1)[0].casefold()
    if command == "/start":
        return "به یارِ یادگیری خوش آمدید. برای پرسش آموزشی از Mini App استفاده کنید."
    if command == "/help":
        return "راهنما: Mini App را باز کنید و پرسش آموزشی خود را ارسال کنید."
    return "پیام شما دریافت شد."


@router.get("/mini-app/config", response_model=MiniAppConfigResponse)
async def mini_app_config() -> MiniAppConfigResponse:
    return MiniAppConfigResponse()


@router.post("/webhook", response_model=TelegramWebhookResponse)
async def telegram_webhook(
    update: dict[str, Any] = Body(default_factory=dict),  # noqa: B008
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
    bot: TelegramBotClient | None = Depends(get_bot_client),  # noqa: B008
) -> TelegramWebhookResponse:
    expected = get_settings().telegram_webhook_secret
    if not expected or not x_telegram_bot_api_secret_token or not hmac.compare_digest(
        x_telegram_bot_api_secret_token, expected
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Telegram webhook secret",
        )
    message = update.get("message")
    if isinstance(message, dict):
        chat = message.get("chat")
        if isinstance(chat, dict) and isinstance(chat.get("id"), int):
            if bot is None:
                raise HTTPException(status_code=503, detail="Telegram integration unavailable")
            try:
                await bot.send_text(chat["id"], reply_for_text(message.get("text")))
            except (RuntimeError, OSError) as exc:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Telegram provider unavailable",
                ) from exc
    return TelegramWebhookResponse()
