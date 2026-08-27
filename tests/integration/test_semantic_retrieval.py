import pytest
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
from app.retrieval.vector_repository import (
    VectorSearchRepository,
)


@pytest.mark.asyncio
async def test_vector_search_returns_closest_chunk() -> None:
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
                name="retrieval-test",
                original_filename=(
                    "retrieval-test.md"
                ),
                source_type="md",
                status="ready",
                file_size_bytes=100,
            )

            session.add(document)

            await session.flush()

            version = DocumentVersion(
                document_id=document.id,
                version_number=1,
                content_hash="c" * 64,
                storage_path=None,
                is_active=True,
            )

            session.add(version)

            await session.flush()

            project_chunk = KnowledgeChunk(
                document_version_id=version.id,
                chunk_index=0,
                content=(
                    "Create New Project instructions."
                ),
                section_title=(
                    "Create New Project"
                ),
                page_number=None,
                token_count=10,
                source_metadata={},
            )

            unrelated_chunk = KnowledgeChunk(
                document_version_id=version.id,
                chunk_index=1,
                content="Project List information.",
                section_title="Project List",
                page_number=None,
                token_count=8,
                source_metadata={},
            )

            session.add_all(
                [
                    project_chunk,
                    unrelated_chunk,
                ]
            )

            await session.flush()

            project_vector = (
                [1.0]
                + [0.0] * 383
            )

            unrelated_vector = (
                [0.0, 1.0]
                + [0.0] * 382
            )

            session.add_all(
                [
                    ChunkEmbedding(
                        chunk_id=project_chunk.id,
                        model_name="fake-model",
                        dimensions=384,
                        embedding=project_vector,
                    ),
                    ChunkEmbedding(
                        chunk_id=unrelated_chunk.id,
                        model_name="fake-model",
                        dimensions=384,
                        embedding=unrelated_vector,
                    ),
                ]
            )

            await session.flush()

            repository = (
                VectorSearchRepository(
                    session
                )
            )

            results = await repository.search(
                query_vector=project_vector,
                limit=2,
            )

            assert len(results) >= 1

            assert (
                results[0].chunk_id
                == project_chunk.id
            )

            assert (
                results[0].section_title
                == "Create New Project"
            )

            await session.rollback()

    finally:
        await engine.dispose()