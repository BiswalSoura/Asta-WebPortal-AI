import pytest

from app.embeddings.embedding_service import (
    EmbeddingService,
)
from app.embeddings.exceptions import (
    EmbeddingDimensionError,
    EmbeddingGenerationError,
)


class FakeEncoder:
    def __init__(
        self,
        dimensions: int = 384,
    ) -> None:
        self.dimensions = dimensions

    def get_sentence_embedding_dimension(
        self,
    ) -> int:
        return self.dimensions

    def encode(
        self,
        sentences: list[str],
        **kwargs,
    ) -> list[list[float]]:
        del kwargs

        return [
            [0.1] * self.dimensions
            for _ in sentences
        ]


def test_embedding_service_returns_vectors() -> None:
    service = EmbeddingService(
        model_name="fake-model",
        device="cpu",
        batch_size=2,
        encoder=FakeEncoder(),
    )

    vectors = service.embed_documents(
        [
            "Login page",
            "Create New Project",
        ]
    )

    assert len(vectors) == 2
    assert len(vectors[0]) == 384
    assert len(vectors[1]) == 384


def test_embedding_service_rejects_wrong_dimension() -> None:
    service = EmbeddingService(
        model_name="fake-model",
        device="cpu",
        batch_size=2,
        encoder=FakeEncoder(
            dimensions=128
        ),
    )

    with pytest.raises(
        EmbeddingDimensionError
    ):
        service.embed_documents(
            ["WebPortal"]
        )


def test_embedding_service_rejects_empty_text() -> None:
    service = EmbeddingService(
        model_name="fake-model",
        device="cpu",
        batch_size=2,
        encoder=FakeEncoder(),
    )

    with pytest.raises(
        EmbeddingGenerationError
    ):
        service.embed_documents(
            ["   "]
        )