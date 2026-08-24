import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from app.core.config import get_settings
from app.database.models import (
    ChunkEmbedding,
    DocumentVersion,
    KnowledgeChunk,
    KnowledgeDocument,
)
from app.database.session import (
    create_database_engine,
)
from app.embeddings.embedding_service import (
    EmbeddingService,
)
from app.services.embedding_indexing import (
    EmbeddingIndexingService,
)


class FakeEncoder:
    def get_sentence_embedding_dimension(
        self,
    ) -> int:
        return 384

    def encode(
        self,
        sentences: list[str],
        **kwargs,
    ) -> list[list[float]]:
        del kwargs

        return [
            [0.1] * 384
            for _ in sentences
        ]


def _embedding_service() -> EmbeddingService:
    return EmbeddingService(
        model_name="fake-model",
        device="cpu",
        batch_size=32,
        encoder=FakeEncoder(),
    )


@pytest.mark.asyncio
async def test_indexes_pending_chunk() -> None:
    settings = get_settings()

    assert settings.test_database_url is not None

    engine = create_database_engine(
        settings.test_database_url
    )

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    try:
        async with session_factory() as session:
            document = KnowledgeDocument(
                name="embedding-test",
                original_filename=(
                    "embedding-test.txt"
                ),
                source_type="txt",
                status="ready",
                file_size_bytes=100,
            )

            session.add(document)

            await session.flush()

            version = DocumentVersion(
                document_id=document.id,
                version_number=1,
                content_hash="a" * 64,
                storage_path=None,
                is_active=True,
            )

            session.add(version)

            await session.flush()

            chunk = KnowledgeChunk(
                document_version_id=version.id,
                chunk_index=0,
                content=(
                    "Create New Project help."
                ),
                section_title=None,
                page_number=None,
                token_count=6,
                source_metadata={},
            )

            session.add(chunk)

            await session.flush()

            service = EmbeddingIndexingService(
                session,
                embedding_service=(
                    _embedding_service()
                ),
            )

            result = await service.index_batch()

            assert result.indexed_chunks == 1

            embedding_result = (
                await session.execute(
                    select(
                        ChunkEmbedding
                    ).where(
                        ChunkEmbedding.chunk_id
                        == chunk.id
                    )
                )
            )

            embedding = (
                embedding_result
                .scalar_one()
            )

            assert embedding.model_name == (
                "fake-model"
            )

            assert embedding.dimensions == 384

            assert len(
                embedding.embedding
            ) == 384

            await session.rollback()

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_existing_embedding_is_not_reindexed() -> None:
    settings = get_settings()

    assert settings.test_database_url is not None

    engine = create_database_engine(
        settings.test_database_url
    )

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    try:
        async with session_factory() as session:
            document = KnowledgeDocument(
                name="existing-embedding-test",
                original_filename=(
                    "existing-embedding-test.txt"
                ),
                source_type="txt",
                status="ready",
                file_size_bytes=100,
            )

            session.add(document)

            await session.flush()

            version = DocumentVersion(
                document_id=document.id,
                version_number=1,
                content_hash="b" * 64,
                storage_path=None,
                is_active=True,
            )

            session.add(version)

            await session.flush()

            chunk = KnowledgeChunk(
                document_version_id=version.id,
                chunk_index=0,
                content="Project List help.",
                section_title=None,
                page_number=None,
                token_count=5,
                source_metadata={},
            )

            session.add(chunk)

            await session.flush()

            existing_embedding = ChunkEmbedding(
                chunk_id=chunk.id,
                model_name="fake-model",
                dimensions=384,
                embedding=[0.1] * 384,
            )

            session.add(existing_embedding)

            await session.flush()

            service = EmbeddingIndexingService(
                session,
                embedding_service=(
                    _embedding_service()
                ),
            )

            result = await service.index_batch()

            assert result.indexed_chunks == 0

            await session.rollback()

    finally:
        await engine.dispose()