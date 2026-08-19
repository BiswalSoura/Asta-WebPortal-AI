from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.constants import (
    DEFAULT_API_V1_PREFIX,
    DEFAULT_LOG_LEVEL,
)


class Settings(BaseSettings):
    app_name: str = "Asta"
    environment: str = "development"
    api_v1_prefix: str = DEFAULT_API_V1_PREFIX
    log_level: str = DEFAULT_LOG_LEVEL

    groq_api_key: str | None = None
    groq_model: str | None = None

    database_url: str | None = None

    embedding_model: str = "BAAI/bge-small-en-v1.5"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="ASTA_",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()