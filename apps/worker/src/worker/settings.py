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


@lru_cache
def get_settings() -> Settings:
    return Settings()
