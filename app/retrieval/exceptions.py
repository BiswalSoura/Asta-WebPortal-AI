from app.core.exceptions import AstaError


class RetrievalError(AstaError):
    """Base exception for Asta retrieval operations."""


class EmptyRetrievalQueryError(RetrievalError):
    def __init__(self) -> None:
        super().__init__(
            "Retrieval query cannot be empty.",
            error_code="EMPTY_RETRIEVAL_QUERY",
        )


class RerankingError(RetrievalError):
    def __init__(self, message: str) -> None:
        super().__init__(
            message,
            error_code="RERANKING_ERROR",
        )