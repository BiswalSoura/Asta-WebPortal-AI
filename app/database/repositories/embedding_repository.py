from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import (
    ChunkEmbedding,
    DocumentVersion,
    KnowledgeChunk,
)


class EmbeddingRepository:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    async def get_pending_chunks(
        self,
        *,
        limit: int,
    ) -> list[KnowledgeChunk]:
        result = await self.session.execute(
            select(KnowledgeChunk)
            .join(
                DocumentVersion,
                DocumentVersion.id
                == KnowledgeChunk.document_version_id,
            )
            .outerjoin(
                ChunkEmbedding,
                ChunkEmbedding.chunk_id
                == KnowledgeChunk.id,
            )
            .where(
                DocumentVersion.is_active.is_(True),
                ChunkEmbedding.id.is_(None),
            )
            .order_by(
                KnowledgeChunk.created_at,
                KnowledgeChunk.chunk_index,
            )
            .limit(limit)
        )

        return list(
            result.scalars().all()
        )

    async def create_embeddings(
        self,
        *,
        chunks: list[KnowledgeChunk],
        vectors: list[list[float]],
        model_name: str,
        dimensions: int,
    ) -> list[ChunkEmbedding]:
        if len(chunks) != len(vectors):
            raise ValueError(
                (
                    "Chunk count and embedding vector "
                    "count must match."
                )
            )

        embeddings = [
            ChunkEmbedding(
                chunk_id=chunk.id,
                model_name=model_name,
                dimensions=dimensions,
                embedding=vector,
            )
            for chunk, vector in zip(
                chunks,
                vectors,
                strict=True,
            )
        ]

        self.session.add_all(
            embeddings
        )

        await self.session.flush()

        return embeddings