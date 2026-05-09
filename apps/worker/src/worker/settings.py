"""Worker configuration via pydantic-settings."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = "postgresql+asyncpg://dealflow:dealflow@localhost:5432/dealflow"
    redis_url: str = "redis://localhost:6379/0"
    log_level: str = "INFO"
    environment: str = "development"
    max_jobs: int = 10
    job_timeout: int = 300

    # Twilio — optional; SMS sending is skipped if not configured
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_from_number: str | None = None

    # OpenAI — optional; LLM scoring falls back to heuristic if not configured
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    # SMTP — optional; email sending is skipped if not configured
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from_address: str | None = None
    smtp_from_name: str = "DealFlow AI"


@lru_cache
def get_settings() -> Settings:
    return Settings()
