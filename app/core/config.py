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

    llm_temperature: float = Field(
        default=0.2,
        validation_alias=AliasChoices(
            "LLM_TEMPERATURE",
            "ASTA_LLM_TEMPERATURE",
        ),
        ge=0.0,
        le=2.0,
    )

    llm_max_tokens: int = Field(
        default=600,
        validation_alias=AliasChoices(
            "LLM_MAX_TOKENS",
            "ASTA_LLM_MAX_TOKENS",
        ),
        ge=1,
    )

    llm_timeout_seconds: float = Field(
        default=30.0,
        validation_alias=AliasChoices(
            "LLM_TIMEOUT_SECONDS",
            "ASTA_LLM_TIMEOUT_SECONDS",
        ),
        gt=0,
    )

    llm_max_retries: int = Field(
        default=2,
        validation_alias=AliasChoices(
            "LLM_MAX_RETRIES",
            "ASTA_LLM_MAX_RETRIES",
        ),
        ge=0,
    )

    database_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "DATABASE_URL",
            "ASTA_DATABASE_URL",
        ),
    )
    test_database_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "TEST_DATABASE_URL",
            "ASTA_TEST_DATABASE_URL",
        ),
    )
    embedding_model: str = Field(
        default="BAAI/bge-small-en-v1.5",
        validation_alias=AliasChoices(
            "EMBEDDING_MODEL",
            "ASTA_EMBEDDING_MODEL",
        ),
    )
    embedding_device: str = Field(
        default="cpu",
        validation_alias=AliasChoices(
            "EMBEDDING_DEVICE",
            "ASTA_EMBEDDING_DEVICE",
        ),
    )
    
    embedding_batch_size: int = Field(
        default=32,
        validation_alias=AliasChoices(
            "EMBEDDING_BATCH_SIZE",
            "ASTA_EMBEDDING_BATCH_SIZE",
        ),
        ge=1,
    )
    reranker_model: str = Field(
        default="cross-encoder/ms-marco-MiniLM-L-6-v2",
        validation_alias=AliasChoices(
            "RERANKER_MODEL",
            "ASTA_RERANKER_MODEL",
        ),
    )

    reranker_device: str = Field(
        default="cpu",
        validation_alias=AliasChoices(
            "RERANKER_DEVICE",
            "ASTA_RERANKER_DEVICE",
        ),
    )

    reranker_min_score: float = Field(
        default=0.5,
        validation_alias=AliasChoices(
            "RERANKER_MIN_SCORE",
            "ASTA_RERANKER_MIN_SCORE",
        ),
        ge=0.0,
        le=1.0,
    )

    retrieval_top_k: int = Field(
        default=8,
        validation_alias=AliasChoices(
            "RETRIEVAL_TOP_K",
            "ASTA_RETRIEVAL_TOP_K",
        ),
        ge=1,
    )

    retrieval_final_k: int = Field(
        default=4,
        validation_alias=AliasChoices(
            "RETRIEVAL_FINAL_K",
            "ASTA_RETRIEVAL_FINAL_K",
        ),
        ge=1,
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="ASTA_",
        case_sensitive=False,
        extra="ignore",
    )

    document_storage_path: str = Field(
        default="data/uploads",
        validation_alias=AliasChoices(
            "DOCUMENT_STORAGE_PATH",
            "ASTA_DOCUMENT_STORAGE_PATH",
        ),
    )

    conversation_history_messages: int = Field(
        default=6,
        validation_alias=AliasChoices(
            "CONVERSATION_HISTORY_MESSAGES",
            "ASTA_CONVERSATION_HISTORY_MESSAGES",
        ),
        ge=1,
        le=20,
    )

    conversation_context_max_chars: int = Field(
        default=4000,
        validation_alias=AliasChoices(
            "CONVERSATION_CONTEXT_MAX_CHARS",
            "ASTA_CONVERSATION_CONTEXT_MAX_CHARS",
        ),
        ge=500,
        le=20000,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()