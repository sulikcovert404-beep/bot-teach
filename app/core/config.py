from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Education Platform Iran"
    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = ""
    telegram_bot_token: str = ""
    telegram_webhook_secret: str = ""
    payment_webhook_secret: str = ""
    gemini_api_key: str = ""
    ai_default_model: str = "gemini-2.0-flash"
    jwt_secret: str = ""
    rate_limit_requests: int = 60
    rate_limit_window_seconds: int = 60

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
