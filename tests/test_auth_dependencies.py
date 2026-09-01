import pytest
from fastapi import HTTPException

from app.core.config import Settings, get_settings
from app.security.dependencies import authorize_role, require_roles, require_user
from app.security.tokens import create_access_token


def test_require_user_rejects_missing_credentials() -> None:
    with pytest.raises(HTTPException) as error:
        require_user(None)
    assert error.value.status_code == 401


def test_require_user_accepts_valid_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "jwt_secret", "x" * 32)
    token = create_access_token("user-1", "x" * 32)
    from fastapi.security import HTTPAuthorizationCredentials

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    assert require_user(credentials) == "user-1"


def test_production_settings_require_security_secrets() -> None:
    with pytest.raises(ValueError, match="Production configuration missing"):
        Settings(_env_file=None, app_env="production")


def test_settings_use_supported_gemini_default_model() -> None:
    settings = Settings(_env_file=None)
    assert settings.ai_default_model == "gemini-3.6-flash"


def test_production_settings_accept_valid_configuration() -> None:
    settings = Settings(
        app_env="production",
        database_url="postgresql+asyncpg://user:pass@db/education",
        jwt_secret="x" * 32,
        telegram_bot_token="telegram-token",
        telegram_webhook_secret="webhook-secret",
        payment_webhook_secret="payment-secret",
        gemini_api_key="gemini-key",
        redis_url="redis://redis:6379/0",
    )
    assert settings.app_env == "production"


def test_production_settings_reject_placeholders() -> None:
    with pytest.raises(ValueError, match="Production configuration missing"):
        Settings(
            _env_file=None,
            app_env="production",
            database_url="postgresql+asyncpg://user:pass@db/education",
            jwt_secret="replace-with-long-random-jwt-secret",
            telegram_bot_token="replace-with-telegram-bot-token",
            telegram_webhook_secret="replace-with-random-webhook-secret",
            payment_webhook_secret="replace-with-random-payment-webhook-secret",
            gemini_api_key="replace-with-gemini-api-key",
        )


def test_production_payment_provider_requires_secure_configuration() -> None:
    with pytest.raises(ValueError, match="PAYMENT_PROVIDER_API_KEY"):
        Settings(
            _env_file=None,
            app_env="production",
            database_url="postgresql+asyncpg://user:pass@db/education",
            jwt_secret="x" * 32,
            telegram_bot_token="telegram-token",
            telegram_webhook_secret="webhook-secret",
            payment_webhook_secret="payment-secret",
            gemini_api_key="gemini-key",
            redis_url="redis://redis:6379/0",
            payment_provider_url="https://gateway.test",
        )

    with pytest.raises(ValueError, match="HTTPS"):
        Settings(
            _env_file=None,
            app_env="production",
            database_url="postgresql+asyncpg://user:pass@db/education",
            jwt_secret="x" * 32,
            telegram_bot_token="telegram-token",
            telegram_webhook_secret="webhook-secret",
            payment_webhook_secret="payment-secret",
            gemini_api_key="gemini-key",
            redis_url="redis://redis:6379/0",
            payment_provider_url="http://gateway.test",
            payment_provider_api_key="provider-key",
        )


def test_authorize_role_rejects_disallowed_role() -> None:
    with pytest.raises(HTTPException) as error:
        authorize_role("STUDENT", {"TEACHER"})
    assert error.value.status_code == 403


def test_require_roles_checks_role_claim(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "jwt_secret", "x" * 32)
    token = create_access_token("user-1", "x" * 32, role="TEACHER")
    from fastapi.security import HTTPAuthorizationCredentials

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    assert require_roles("TEACHER")(credentials) == "user-1"
