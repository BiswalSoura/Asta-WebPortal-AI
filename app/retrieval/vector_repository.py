from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import (
    ChunkEmbedding,
    DocumentVersion,
    KnowledgeChunk,
    KnowledgeDocument,
)
from app.retrieval.models import (
    RetrievalCandidate,
)


class VectorSearchRepository:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    async def search(
        self,
        *,
        query_vector: list[float],
        limit: int,
    ) -> list[RetrievalCandidate]:
        distance = (
            ChunkEmbedding.embedding
            .cosine_distance(query_vector)
        )

        statement = (
            select(
                KnowledgeChunk,
                KnowledgeDocument,
                distance.label(
                    "vector_distance"
                ),
            )
            .join(
                ChunkEmbedding,
                ChunkEmbedding.chunk_id
                == KnowledgeChunk.id,
            )
            .join(
                DocumentVersion,
                DocumentVersion.id
                == KnowledgeChunk.document_version_id,
            )
            .join(
                KnowledgeDocument,
                KnowledgeDocument.id
                == DocumentVersion.document_id,
            )
            .where(
                DocumentVersion.is_active.is_(True),
                KnowledgeDocument.status
                == "ready",
            )
            .order_by(distance)
            .limit(limit)
        )

        result = await self.session.execute(
            statement
        )

        candidates: list[
            RetrievalCandidate
        ] = []

        for (
            chunk,
            document,
            vector_distance,
        ) in result.all():
            similarity = (
                1.0
                - float(vector_distance)
            )

            candidates.append(
                RetrievalCandidate(
                    chunk_id=chunk.id,
                    document_id=document.id,
                    document_name=document.name,
                    original_filename=(
                        document.original_filename
                    ),
                    content=chunk.content,
                    section_title=(
                        chunk.section_title
                    ),
                    page_number=(
                        chunk.page_number
                    ),
                    source_metadata=(
                        chunk.source_metadata
                    ),
                    vector_score=similarity,
                )
            )

        return candidates