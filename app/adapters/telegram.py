import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import parse_qs


@dataclass(frozen=True)
class TelegramIdentity:
    telegram_user_id: int
    username: str | None = None


class TelegramAdapter(Protocol):
    async def send_text(self, chat_id: int, text: str) -> None: ...


def validate_web_app_init_data(
    init_data: str,
    bot_token: str,
    *,
    max_age_seconds: int = 86_400,
    now: int | None = None,
) -> TelegramIdentity:
    """Validate Telegram Web App initData and return the signed user identity."""
    if not init_data or not bot_token or max_age_seconds < 1:
        raise ValueError("Telegram initData and bot token are required")
    values = parse_qs(init_data, strict_parsing=True)
    received_hash = values.pop("hash", [None])[0]
    if not received_hash:
        raise ValueError("Telegram initData hash is required")
    check_string = "\n".join(
        f"{key}={items[0]}" for key, items in sorted(values.items()) if items
    )
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected_hash = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(received_hash, expected_hash):
        raise ValueError("Invalid Telegram initData signature")
    auth_date_raw = values.get("auth_date", [None])[0]
    try:
        auth_date = int(auth_date_raw) if auth_date_raw is not None else 0
    except ValueError as exc:
        raise ValueError("Invalid Telegram auth_date") from exc
    current_time = int(time.time()) if now is None else now
    if auth_date <= 0 or current_time - auth_date > max_age_seconds or auth_date > current_time + 60:
        raise ValueError("Expired Telegram initData")
    user_raw = values.get("user", [None])[0]
    try:
        user = json.loads(user_raw) if user_raw else {}
        telegram_user_id = int(user["id"])
        if telegram_user_id < 1:
            raise ValueError("Telegram user identity is invalid")
    except (TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        raise ValueError("Telegram user identity is invalid") from exc
    return TelegramIdentity(telegram_user_id=telegram_user_id, username=user.get("username"))
