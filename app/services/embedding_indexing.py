from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.database.models.knowledge import (
    EMBEDDING_DIMENSION,
)
from app.database.repositories import (
    EmbeddingRepository,
)
from app.embeddings import (
    EmbeddingIndexResult,
    EmbeddingService,
)


class EmbeddingIndexingService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        settings = get_settings()

        self.repository = EmbeddingRepository(
            session
        )

        self.embedding_service = (
            embedding_service
            or EmbeddingService(
                model_name=settings.embedding_model,
                device=settings.embedding_device,
                batch_size=(
                    settings.embedding_batch_size
                ),
            )
        )

        self.batch_size = (
            settings.embedding_batch_size
        )

    async def index_batch(
        self,
    ) -> EmbeddingIndexResult:
        chunks = (
            await self.repository
            .get_pending_chunks(
                limit=self.batch_size
            )
        )

        if not chunks:
            return EmbeddingIndexResult(
                indexed_chunks=0,
                model_name=(
                    self.embedding_service.model_name
                ),
                dimensions=EMBEDDING_DIMENSION,
            )

        texts = [
            chunk.content
            for chunk in chunks
        ]

        vectors = (
            self.embedding_service
            .embed_documents(texts)
        )

        await self.repository.create_embeddings(
            chunks=chunks,
            vectors=vectors,
            model_name=(
                self.embedding_service.model_name
            ),
            dimensions=EMBEDDING_DIMENSION,
        )

        return EmbeddingIndexResult(
            indexed_chunks=len(chunks),
            model_name=(
                self.embedding_service.model_name
            ),
            dimensions=EMBEDDING_DIMENSION,
        )