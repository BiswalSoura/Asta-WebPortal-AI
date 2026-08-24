from typing import Any, Protocol

from app.database.models.knowledge import (
    EMBEDDING_DIMENSION,
)
from app.embeddings.exceptions import (
    EmbeddingDimensionError,
    EmbeddingGenerationError,
)


class EmbeddingEncoder(Protocol):
    def get_sentence_embedding_dimension(
        self,
    ) -> int | None:
        ...

    def encode(
        self,
        sentences: list[str],
        **kwargs: Any,
    ) -> Any:
        ...


class EmbeddingService:
    def __init__(
        self,
        *,
        model_name: str,
        device: str,
        batch_size: int,
        encoder: EmbeddingEncoder | None = None,
        expected_dimensions: int = EMBEDDING_DIMENSION,
    ) -> None:
        self.model_name = model_name
        self.device = device
        self.batch_size = batch_size
        self.expected_dimensions = expected_dimensions
        self._encoder = encoder

    def embed_documents(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        if not texts:
            return []

        if any(not text.strip() for text in texts):
            raise EmbeddingGenerationError(
                "Cannot generate embeddings for empty text."
            )

        encoder = self._get_encoder()

        self._validate_model_dimension(
            encoder
        )

        try:
            raw_vectors = encoder.encode(
                texts,
                batch_size=self.batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True,
            )

        except Exception as exc:
            raise EmbeddingGenerationError(
                "Failed to generate document embeddings."
            ) from exc

        vectors = (
            raw_vectors.tolist()
            if hasattr(raw_vectors, "tolist")
            else [
                list(vector)
                for vector in raw_vectors
            ]
        )

        if len(vectors) != len(texts):
            raise EmbeddingGenerationError(
                (
                    "Embedding model returned an unexpected "
                    "number of vectors."
                )
            )

        for vector in vectors:
            actual_dimensions = len(vector)

            if (
                actual_dimensions
                != self.expected_dimensions
            ):
                raise EmbeddingDimensionError(
                    expected=self.expected_dimensions,
                    actual=actual_dimensions,
                )

        return vectors

    def _get_encoder(
        self,
    ) -> EmbeddingEncoder:
        if self._encoder is None:
            from sentence_transformers import (
                SentenceTransformer,
            )

            self._encoder = SentenceTransformer(
                self.model_name,
                device=self.device,
            )

        return self._encoder

    def _validate_model_dimension(
        self,
        encoder: EmbeddingEncoder,
    ) -> None:
        dimensions = (
            encoder
            .get_sentence_embedding_dimension()
        )

        if (
            dimensions is not None
            and dimensions
            != self.expected_dimensions
        ):
            raise EmbeddingDimensionError(
                expected=self.expected_dimensions,
                actual=dimensions,
            )