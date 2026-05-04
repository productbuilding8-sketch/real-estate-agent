from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "DealFlow AI"
    app_version: str = "0.1.0"
    environment: Literal["development", "test", "staging", "production"] = "development"
    log_level: str = "INFO"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://dealflow:dealflow@localhost:5432/dealflow"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Auth0
    auth0_domain: str = ""
    auth0_audience: str = ""

    # Secrets
    secret_key: str = ""

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def postgres_dsn(self) -> str:
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
