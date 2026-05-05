from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Core
    app_env: str = "development"
    app_secret_key: str = "insecure-dev-key"
    log_level: str = "INFO"

    # DB
    database_url: str = "postgresql+psycopg://medspa:medspa@localhost:5432/medspa"

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"

    # Auth
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 720
    access_token_cookie_name: str = "medspa_session"

    # OpenAI
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_live: bool = False

    # Twilio
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_from_number: str | None = None
    twilio_validate_signature: bool = True
    twilio_live: bool = False

    # Email
    email_provider: str = "resend"  # or sendgrid
    resend_api_key: str | None = None
    sendgrid_api_key: str | None = None
    email_from: str = "no-reply@medspa-assistant.local"
    email_live: bool = False

    # Demo
    demo_twilio_number: str | None = None
    demo_max_messages_per_24h: int = 10

    # LemonSqueezy
    lemonsqueezy_signing_secret: str | None = None
    lemonsqueezy_store_id: str | None = None
    lemonsqueezy_variant_id_starter: str | None = None
    lemonsqueezy_variant_id_pro: str | None = None

    # CORS
    cors_origins: str = "http://localhost:3000"

    # App URL (for email links)
    app_url: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def validate_production(self) -> List[str]:
        """Return a list of fatal config problems for production. Empty == OK."""
        problems: list[str] = []
        if self.app_env != "production":
            return problems
        if len(self.app_secret_key) < 32 or self.app_secret_key.startswith("insecure"):
            problems.append("APP_SECRET_KEY must be ≥32 chars and not the dev default")
        if self.openai_live and not self.openai_api_key:
            problems.append("OPENAI_LIVE=true but OPENAI_API_KEY is empty")
        if "localhost" in self.database_url or "127.0.0.1" in self.database_url:
            problems.append("DATABASE_URL points at localhost in production")
        if not self.cors_origins_list or "*" in self.cors_origins:
            problems.append("CORS_ORIGINS must be an explicit list, never '*'")
        if not self.twilio_validate_signature or not self.twilio_auth_token:
            problems.append(
                "TWILIO_VALIDATE_SIGNATURE must be true and TWILIO_AUTH_TOKEN set"
            )
        return problems


@lru_cache
def get_settings() -> Settings:
    return Settings()
