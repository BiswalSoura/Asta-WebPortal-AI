from functools import lru_cache

from pydantic import AliasChoices, Field
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

    groq_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "GROQ_API_KEY",
            "ASTA_GROQ_API_KEY",
        ),
    )

    groq_model: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "GROQ_MODEL",
            "ASTA_GROQ_MODEL",
        ),
    )

    database_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "DATABASE_URL",
            "ASTA_DATABASE_URL",
        ),
    )

    embedding_model: str = Field(
        default="BAAI/bge-small-en-v1.5",
        validation_alias=AliasChoices(
            "EMBEDDING_MODEL",
            "ASTA_EMBEDDING_MODEL",
        ),
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="ASTA_",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()