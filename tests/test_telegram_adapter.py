import hashlib
import hmac
import json
from urllib.parse import quote

import pytest

from app.adapters.telegram import validate_web_app_init_data


def signed_init_data(bot_token: str, auth_date: int) -> str:
    user = json.dumps({"id": 123, "username": "student"}, separators=(",", ":"))
    data = f"auth_date={auth_date}\nuser={user}"
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    signature = hmac.new(secret, data.encode(), hashlib.sha256).hexdigest()
    return f"auth_date={auth_date}&user={quote(user)}&hash={signature}"


def test_validate_web_app_init_data_returns_identity() -> None:
    identity = validate_web_app_init_data(
        signed_init_data("token", 1_000), "token", now=1_100
    )
    assert identity.telegram_user_id == 123
    assert identity.username == "student"


def test_validate_web_app_init_data_rejects_bad_signature() -> None:
    with pytest.raises(ValueError, match="signature"):
        validate_web_app_init_data(signed_init_data("token", 1_000), "wrong", now=1_100)


def test_validate_web_app_init_data_rejects_expired_data() -> None:
    with pytest.raises(ValueError, match="Expired"):
        validate_web_app_init_data(signed_init_data("token", 1_000), "token", now=90_000)
