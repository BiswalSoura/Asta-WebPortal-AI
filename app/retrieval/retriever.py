from typing import Protocol

from app.retrieval.exceptions import (
    EmptyRetrievalQueryError,
)
from app.retrieval.models import (
    RetrievalCandidate,
)
from app.retrieval.vector_repository import (
    VectorSearchRepository,
)


class QueryEmbeddingService(Protocol):
    def embed_documents(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        ...


class SemanticRetriever:
    def __init__(
        self,
        *,
        embedding_service: QueryEmbeddingService,
        repository: VectorSearchRepository,
    ) -> None:
        self.embedding_service = (
            embedding_service
        )

        self.repository = repository

    async def retrieve(
        self,
        query: str,
        *,
        limit: int,
    ) -> list[RetrievalCandidate]:
        normalized_query = query.strip()

        if not normalized_query:
            raise EmptyRetrievalQueryError()

        vectors = (
            self.embedding_service
            .embed_documents(
                [normalized_query]
            )
        )

        query_vector = vectors[0]

        return await self.repository.search(
            query_vector=query_vector,
            limit=limit,
        )