import hashlib
import hmac
import logging
from typing import Any

from fastapi import APIRouter, Body, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.auth import get_session
from app.core.channels import CanonicalCommand, Channel, ChannelContext
from app.core.config import get_settings
from app.core.logging import telegram_metrics
from app.db.models import TelegramUpdate
from app.services.audit_repository import record_audit_log
from app.services.notification import telegram_notifications
from app.services.telegram_bot import TelegramAPIError, TelegramBotClient
from app.services.telegram_navigation import (
    NavigationConfig,
    allowed_callback,
    build_inline_keyboard,
    build_reply_keyboard,
    build_role_keyboard,
    build_start_inline_keyboard,
    fallback_text,
    web_app_url_for_role,
)
from app.services.telegram_tutor import resolve_telegram_identity
from app.services.telegram_ui import confirmation_message, main_menu

router = APIRouter(prefix="/telegram", tags=["telegram"])
logger = logging.getLogger(__name__)


class TelegramWebhookResponse(BaseModel):
    accepted: bool = True


class MiniAppConfigResponse(BaseModel):
    api_version: str = "v1"
    platform: str = "telegram-mini-app"
    auth_endpoint: str = "/api/v1/auth/telegram"


def navigation_payload(*, web_app_url: str) -> dict[str, object]:
    """Build navigation markup for controlled integration tests; do not send."""
    config = NavigationConfig(web_app_url)
    return {
        "reply_markup": build_reply_keyboard(web_app_url=web_app_url),
        "inline_markup": build_inline_keyboard(config),
    }
def callback_reply(callback_data: str | None) -> str | None:
    """Resolve only allowlisted callbacks; unknown data gets safe fallback."""
    if callback_data is None or allowed_callback(callback_data) is not None:
        return None
    return fallback_text(callback_data)


def get_bot_client() -> TelegramBotClient | None:
    token = get_settings().telegram_bot_token
    return TelegramBotClient(token) if token else None


def reply_for_text(text: str | None) -> str:
    command = (text or "").strip().split(maxsplit=1)[0].casefold()
    if command == "/start":
        return "سلام 👋\nبه یارِ یادگیری خوش آمدید.\n\n" + main_menu(None).text
    if command == "/help":
        return confirmation_message("راهنما: از منوی پایین وارد کلاس هوشمند شوید یا /start را دوباره بفرستید.").text
    # Reply-keyboard labels are navigation intents, not tutor prompts. Keep
    # their response neutral until the authenticated Mini App loads the real
    # tenant-scoped data, avoiding fabricated classroom or progress content.
    label = (text or "").strip()
    if label in {"🏠 خانه", "🏫 کلاس‌های من", "📚 درس‌های من", "📝 تمرین‌ها", "📊 پیشرفت", "📊 پیشرفت من", "🤖 کمک هوشمند", "📥 صف بررسی", "📚 محتوا"}:
        return confirmation_message("برای نمایش اطلاعات واقعی، دکمه مربوط را در مینی‌اپ باز کنید.").text
    return confirmation_message("پیام شما دریافت شد.").text


def is_navigation_label(text: str | None) -> bool:
    return (text or "").strip() in {
        "🏠 خانه", "🏫 کلاس‌های من", "📚 درس‌های من", "📝 تمرین‌ها",
        "📊 پیشرفت", "📊 پیشرفت من", "🤖 کمک هوشمند", "📥 صف بررسی", "📚 محتوا",
    }


@router.get("/mini-app/config", response_model=MiniAppConfigResponse)
async def mini_app_config() -> MiniAppConfigResponse:
    return MiniAppConfigResponse()


@router.post("/webhook", response_model=TelegramWebhookResponse)
async def telegram_webhook(
    update: dict[str, Any] = Body(default_factory=dict),  # noqa: B008
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
    bot: TelegramBotClient | None = Depends(get_bot_client),
    session: AsyncSession = Depends(get_session),
) -> TelegramWebhookResponse:
    telegram_metrics.webhook_request()
    expected = get_settings().telegram_webhook_secret
    if (
        not expected
        or not x_telegram_bot_api_secret_token
        or not hmac.compare_digest(x_telegram_bot_api_secret_token, expected)
    ):
        telegram_metrics.webhook_validation_failure("missing_secret" if not x_telegram_bot_api_secret_token else "invalid_secret")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Telegram webhook secret",
        )
    callback = update.get("callback_query")
    if isinstance(callback, dict):
        callback_update_id = update.get("update_id")
        if isinstance(callback_update_id, int):
            session.add(TelegramUpdate(update_id=callback_update_id))
            try:
                await session.flush()
            except IntegrityError:
                await session.rollback()
                return TelegramWebhookResponse()
        cm = callback.get("message")
        chat = cm.get("chat") if isinstance(cm, dict) else None
        if bot is None or not isinstance(chat, dict) or not isinstance(chat.get("id"), int):
            telegram_metrics.dependency_failure("bot_unavailable")
            raise HTTPException(status_code=503, detail="Telegram integration unavailable")
        text = callback_response(callback.get("data") if isinstance(callback.get("data"), str) else None)
        try:
            await telegram_notifications(bot).send(Channel.TELEGRAM, str(chat["id"]), text, notification_id=str(update.get("update_id", chat["id"])))
        except TelegramAPIError as exc:
            if 400 <= exc.http_status < 500:
                await session.commit()
                return TelegramWebhookResponse()
            await session.rollback()
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Telegram provider unavailable") from exc
        await session.commit()
        return TelegramWebhookResponse()
    message = update.get("message")
    if isinstance(message, dict):
        update_id = update.get("update_id")
        logger.info("telegram_webhook_received update_id=%s update_type=message", update_id if isinstance(update_id, int) else "unknown")
        chat = message.get("chat")
        text = message.get("text")
        if isinstance(chat, dict) and isinstance(chat.get("id"), int):
            if bot is None:
                telegram_metrics.dependency_failure("bot_unavailable")
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
            markup = None
            command = (text or "").strip().split(maxsplit=1)[0].casefold() if isinstance(text, str) else ""
            if command in {"/start", "/help"}:
                markup = navigation_payload(web_app_url=get_settings().telegram_web_app_url)["reply_markup"]
                logger.info("telegram_start_handler_matched update_id=%s keyboard_built=%s", update_id if isinstance(update_id, int) else "unknown", markup is not None)
            sender = message.get("from")
            if (
                isinstance(text, str)
                and text.strip()
                and not text.lstrip().startswith("/")
                and not is_navigation_label(text)
                and isinstance(sender, dict)
                and isinstance(sender.get("id"), int)
            ):
                reply = await educational_reply(
                    text=text,
                    telegram_user=sender,
                    session=session,
                )
            # Build a canonical command at the adapter boundary while preserving
            # the existing reply and keyboard behavior.
            sender_id = sender.get("id") if isinstance(sender, dict) and isinstance(sender.get("id"), int) else chat["id"]
            resolved_user = None
            resolved_tenant = None
            if isinstance(sender, dict) and isinstance(sender.get("id"), int):
                resolved_user, resolved_tenant = await resolve_telegram_identity(session, sender_id)
            if command == "/owner-identity-check":
                markup = None
                if resolved_user is None:
                    reply = "OWNER IDENTITY NOT FOUND\nCanonical account could not be resolved."
                    await record_audit_log(
                        session,
                        actor_user_id=None,
                        action="owner_identity_check",
                        resource_type="telegram_identity",
                        resource_id="unresolved",
                        metadata={"resolved": False},
                    )
                else:
                    fingerprint = hashlib.sha256(str(resolved_user.id).encode("utf-8")).hexdigest()[:8].upper()
                    reply = (
                        "OWNER IDENTITY VERIFIED\n"
                        "Canonical account found\n"
                        f"Current role: {resolved_user.role}\n"
                        f"Fingerprint: {fingerprint}"
                    )
                    await record_audit_log(
                        session,
                        actor_user_id=resolved_user.id,
                        action="owner_identity_check",
                        resource_type="telegram_identity",
                        resource_id=fingerprint,
                        metadata={"resolved": True, "canonical_user_fingerprint": fingerprint},
                    )
            if command == "/start":
                web_app_url = get_settings().telegram_web_app_url
                if web_app_url:
                    role = resolved_user.role if resolved_user is not None else None
                    markup = build_start_inline_keyboard(
                        web_app_url_for_role(web_app_url, role),
                        label="🎓 ورود به پنل آموزشی",
                    )
                elif resolved_user is not None:
                    reply = confirmation_message(main_menu(resolved_user.role).text).text
                    markup = build_role_keyboard(resolved_user.role)
            context = ChannelContext(
                channel=Channel.TELEGRAM,
                user_id=resolved_user.id if resolved_user is not None else None,
                tenant_id=resolved_tenant,
                trace_id=f"telegram:{update.get('update_id', 'unknown')}",
            )
            CanonicalCommand(
                name="telegram.message",
                payload={"text": text or "", "chat_id": chat["id"], "sender_id": sender_id},
                context=context,
                request_id=str(update.get("update_id", chat["id"])),
            )
            try:
                logger.info("telegram_send_attempted update_id=%s has_markup=%s", update_id if isinstance(update_id, int) else "unknown", markup is not None)
                if markup is None:
                    await telegram_notifications(bot).send(
                        Channel.TELEGRAM, str(chat["id"]), reply,
                        notification_id=str(update.get("update_id", chat["id"])),
                    )
                else:
                    await telegram_notifications(bot).send(
                        Channel.TELEGRAM, str(chat["id"]), reply,
                        notification_id=str(update.get("update_id", chat["id"])),
                        metadata={"reply_markup": markup},
                    )
            except TelegramAPIError as exc:
                logger.warning("telegram_send_result update_id=%s provider_http_status=%s provider_error_code=%s provider_description=%s result=error", update_id if isinstance(update_id, int) else "unknown", exc.http_status, exc.error_code, exc.description)
                # Permanent destination errors (blocked bot, invalid chat) must be
                # acknowledged so Telegram does not poison the webhook with retries.
                if 400 <= exc.http_status < 500:
                    await session.commit()
                    return TelegramWebhookResponse()
                await session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Telegram provider unavailable",
                ) from exc
            except (RuntimeError, OSError) as exc:
                await session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Telegram provider unavailable",
                ) from exc
            await session.commit()
            logger.info("telegram_send_result update_id=%s provider_http_status=200 result=success", update_id if isinstance(update_id, int) else "unknown")
    return TelegramWebhookResponse()



from app.services.telegram_mcq import callback_response
from app.services.telegram_tutor import answer_telegram_text as educational_reply
