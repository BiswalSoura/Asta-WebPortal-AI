from app.core.exceptions import AstaError


class EmbeddingError(AstaError):
    """Base exception for Asta embedding operations."""


class EmbeddingDimensionError(EmbeddingError):
    def __init__(
        self,
        expected: int,
        actual: int,
    ) -> None:
        super().__init__(
            (
                "Embedding dimension mismatch. "
                f"Expected {expected}, received {actual}."
            ),
            error_code="EMBEDDING_DIMENSION_ERROR",
        )


class EmbeddingGenerationError(EmbeddingError):
    def __init__(
        self,
        message: str,
    ) -> None:
        super().__init__(
            message,
            error_code="EMBEDDING_GENERATION_ERROR",
        )