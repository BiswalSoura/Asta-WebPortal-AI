from uuid import uuid4

import pytest

from app.retrieval.exceptions import (
    EmptyRetrievalQueryError,
)
from app.retrieval.models import (
    RetrievalCandidate,
)
from app.retrieval.retriever import (
    SemanticRetriever,
)


class FakeEmbeddingService:
    def embed_documents(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        assert texts == [
            "How do I create a project?"
        ]

        return [
            [1.0] + [0.0] * 383
        ]


class FakeRepository:
    async def search(
        self,
        *,
        query_vector: list[float],
        limit: int,
    ) -> list[RetrievalCandidate]:
        assert len(query_vector) == 384
        assert limit == 8

        return [
            RetrievalCandidate(
                chunk_id=uuid4(),
                document_id=uuid4(),
                document_name="WebPortal Guide",
                original_filename=(
                    "webportal-guide.md"
                ),
                content=(
                    "Use Create New Project."
                ),
                section_title=(
                    "Create New Project"
                ),
                page_number=None,
                source_metadata={},
                vector_score=0.91,
            )
        ]


@pytest.mark.asyncio
async def test_retriever_returns_candidates() -> None:
    retriever = SemanticRetriever(
        embedding_service=(
            FakeEmbeddingService()
        ),
        repository=FakeRepository(),
    )

    results = await retriever.retrieve(
        "How do I create a project?",
        limit=8,
    )

    assert len(results) == 1

    assert (
        results[0].section_title
        == "Create New Project"
    )


@pytest.mark.asyncio
async def test_retriever_rejects_empty_query() -> None:
    retriever = SemanticRetriever(
        embedding_service=(
            FakeEmbeddingService()
        ),
        repository=FakeRepository(),
    )

    with pytest.raises(
        EmptyRetrievalQueryError
    ):
        await retriever.retrieve(
            "   ",
            limit=8,
        )