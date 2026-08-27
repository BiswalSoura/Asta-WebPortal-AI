from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.embeddings import EmbeddingService
from app.retrieval import (
    CrossEncoderReranker,
    RetrievalCandidate,
    SemanticRetriever,
    VectorSearchRepository,
)


class KnowledgeRetrievalService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        embedding_service: EmbeddingService
        | None = None,
        reranker: CrossEncoderReranker
        | None = None,
    ) -> None:
        settings = get_settings()

        embedding_service = (
            embedding_service
            or EmbeddingService(
                model_name=(
                    settings.embedding_model
                ),
                device=(
                    settings.embedding_device
                ),
                batch_size=(
                    settings.embedding_batch_size
                ),
            )
        )

        repository = VectorSearchRepository(
            session
        )

        self.retriever = SemanticRetriever(
            embedding_service=(
                embedding_service
            ),
            repository=repository,
        )

        self.reranker = (
            reranker
            or CrossEncoderReranker(
                model_name=(
                    settings.reranker_model
                ),
                device=(
                    settings.reranker_device
                ),
            )
        )

        self.retrieval_top_k = (
            settings.retrieval_top_k
        )

        self.retrieval_final_k = (
            settings.retrieval_final_k
        )

        self.reranker_min_score = (
            settings.reranker_min_score
        )

    async def search(
        self,
        query: str,
    ) -> list[RetrievalCandidate]:
        candidates = (
            await self.retriever.retrieve(
                query,
                limit=self.retrieval_top_k,
            )
        )

        return self.reranker.rerank(
            query,
            candidates,
            top_k=self.retrieval_final_k,
            min_score=self.reranker_min_score,
        )