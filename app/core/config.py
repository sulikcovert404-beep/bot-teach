from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Education Platform Iran"
    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = ""
    telegram_bot_token: str = ""
    telegram_webhook_secret: str = ""
    payment_webhook_secret: str = ""
    payment_provider_url: str = ""
    payment_provider_api_key: str = ""
    gemini_api_key: str = ""
    ai_default_model: str = "gemini-3.6-flash"
    jwt_secret: str = ""
    rate_limit_requests: int = 60
    rate_limit_window_seconds: int = 60
    redis_url: str = ""
    cors_allowed_origins: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        secrets_dir="/run/secrets" if Path("/run/secrets").is_dir() else None,
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_production_requirements(self) -> "Settings":
        if self.app_env.lower() != "production":
            return self
        required = {
            "DATABASE_URL": self.database_url,
            "JWT_SECRET": self.jwt_secret,
            "TELEGRAM_BOT_TOKEN": self.telegram_bot_token,
            "TELEGRAM_WEBHOOK_SECRET": self.telegram_webhook_secret,
            "PAYMENT_WEBHOOK_SECRET": self.payment_webhook_secret,
            "GEMINI_API_KEY": self.gemini_api_key,
            "REDIS_URL": self.redis_url,
        }
        missing = [
            name
            for name, value in required.items()
            if not value.strip() or value.strip().lower().startswith("replace-with-")
        ]
        if missing:
            raise ValueError(f"Production configuration missing: {', '.join(missing)}")
        if len(self.jwt_secret) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters in production")
        if self.payment_provider_url.strip():
            if not self.payment_provider_api_key.strip():
                raise ValueError("PAYMENT_PROVIDER_API_KEY is required when a payment provider is configured")
            if not self.payment_provider_url.startswith("https://"):
                raise ValueError("PAYMENT_PROVIDER_URL must use HTTPS in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
