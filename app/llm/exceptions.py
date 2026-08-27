from app.core.exceptions import AstaError


class LLMError(AstaError):
    """Base exception for Asta LLM operations."""


class LLMConfigurationError(LLMError):
    def __init__(self, message: str) -> None:
        super().__init__(
            message,
            error_code="LLM_CONFIGURATION_ERROR",
        )


class LLMRequestError(LLMError):
    def __init__(self, message: str) -> None:
        super().__init__(
            message,
            error_code="LLM_REQUEST_ERROR",
        )


class EmptyLLMResponseError(LLMError):
    def __init__(self) -> None:
        super().__init__(
            "The language model returned an empty response.",
            error_code="EMPTY_LLM_RESPONSE",
        )