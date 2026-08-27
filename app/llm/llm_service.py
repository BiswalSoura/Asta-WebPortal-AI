from app.core.config import get_settings
from app.llm.exceptions import (
    LLMConfigurationError,
)
from app.llm.groq_client import (
    GroqLLMClient,
)


def create_llm_client() -> GroqLLMClient:
    settings = get_settings()

    if not settings.groq_api_key:
        raise LLMConfigurationError(
            "GROQ_API_KEY is not configured."
        )

    if not settings.groq_model:
        raise LLMConfigurationError(
            "GROQ_MODEL is not configured."
        )

    return GroqLLMClient(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        timeout_seconds=(
            settings.llm_timeout_seconds
        ),
        max_retries=settings.llm_max_retries,
    )