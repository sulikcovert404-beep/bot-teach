import hmac
from typing import Any

from fastapi import APIRouter, Body, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.auth import get_session
from app.core.config import get_settings
from app.db.models import Subscription, TelegramUpdate, User
from app.domain.entitlements.models import FeatureCode
from app.domain.entitlements.service import entitlement_for_subscription
from app.services.ai_gateway import GeminiProvider, ModelRouter
from app.services.ai_tutor import AITutor
from app.services.document_ingestion import DatabaseRetriever
from app.services.telegram_bot import TelegramBotClient
from app.services.usage_repository import record_usage

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
    session: AsyncSession = Depends(get_session),  # noqa: B008
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
        text = message.get("text")
        if isinstance(chat, dict) and isinstance(chat.get("id"), int):
            if bot is None:
                raise HTTPException(status_code=503, detail="Telegram integration unavailable")
            update_id = update.get("update_id")
            if isinstance(update_id, int):
                session.add(TelegramUpdate(update_id=update_id))
                try:
                    await session.flush()
                except IntegrityError:
                    await session.rollback()
                    return TelegramWebhookResponse()
            reply = reply_for_text(text if isinstance(text, str) else None)
            sender = message.get("from")
            if (
                isinstance(text, str)
                and text.strip()
                and not text.lstrip().startswith("/")
                and isinstance(sender, dict)
                and isinstance(sender.get("id"), int)
            ):
                reply = await educational_reply(
                    text=text,
                    telegram_user=sender,
                    session=session,
                )
            try:
                await bot.send_text(chat["id"], reply)
            except (RuntimeError, OSError) as exc:
                await session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Telegram provider unavailable",
                ) from exc
            await session.commit()
    return TelegramWebhookResponse()


async def educational_reply(
    *,
    text: str,
    telegram_user: object,
    session: AsyncSession,
) -> str:
    """Answer a Telegram text message through the same entitled tutor flow."""
    if not isinstance(telegram_user, dict) or not isinstance(telegram_user.get("id"), int):
        return "برای استفاده از دستیار آموزشی، پیام را از یک حساب معتبر تلگرام ارسال کنید."
    telegram_id = telegram_user["id"]
    user = await session.scalar(select(User).where(User.telegram_user_id == telegram_id))
    if user is None:
        user = User(
            telegram_user_id=telegram_id,
            username=telegram_user.get("username") if isinstance(telegram_user.get("username"), str) else None,
        )
        session.add(user)
        await session.flush()
    subscription = await session.scalar(select(Subscription).where(Subscription.user_id == user.id))
    entitlement = entitlement_for_subscription(
        subscription.plan if subscription else "FREE",
        subscription.active_until if subscription else None,
    )
    if not entitlement.allows(FeatureCode.AI_CHAT):
        return "دسترسی گفت‌وگوی هوشمند برای حساب شما فعال نیست."
    settings = get_settings()
    if not settings.gemini_api_key:
        return "سرویس هوش مصنوعی موقتاً در دسترس نیست."
    try:
        result = await AITutor(
            GeminiProvider(settings.gemini_api_key),
            ModelRouter(settings.ai_default_model),
            DatabaseRetriever(session),
        ).answer(text)
    except RuntimeError:
        return "پاسخ‌گویی هوشمند موقتاً با مشکل مواجه شد. لطفاً دوباره تلاش کنید."
    requested_tokens = 1_200
    await record_usage(
        session,
        user_id=user.id,
        task_type="ai_tutor",
        model=result.model,
        requested_tokens=requested_tokens,
        charged_tokens=(
            min(result.usage_tokens, requested_tokens)
            if result.usage_tokens is not None
            else requested_tokens
        ),
    )
    await session.commit()
    return result.text
