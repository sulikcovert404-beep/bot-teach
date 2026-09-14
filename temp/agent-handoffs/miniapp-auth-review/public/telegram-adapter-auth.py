"""Sanitized auth validation excerpt from app/adapters/telegram.py."""
import hashlib, hmac, json, time
from urllib.parse import parse_qs

def validate_web_app_init_data(init_data: str, bot_token: str, *, max_age_seconds: int = 86400, now: int | None = None):
    values = parse_qs(init_data, strict_parsing=True)
    received_hash = values.pop("hash", [None])[0]
    check_string = "\n".join(f"{key}={items[0]}" for key, items in sorted(values.items()) if items)
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected_hash = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()
    if not received_hash or not hmac.compare_digest(received_hash, expected_hash):
        raise ValueError("Invalid Telegram initData signature")
    auth_date = int(values.get("auth_date", [0])[0])
    current_time = int(time.time()) if now is None else now
    if auth_date <= 0 or current_time - auth_date > max_age_seconds or auth_date > current_time + 60:
        raise ValueError("Expired Telegram initData")
    user = json.loads(values.get("user", ["{}"]) [0])
    return int(user["id"]), user.get("username")

