from pathlib import Path

import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.database.models import (
    DocumentVersion,
    KnowledgeChunk,
    KnowledgeDocument,
)
from app.database.session import (
    create_database_engine,
)
from app.services.document_storage import (
    LocalDocumentStorage,
)
from app.services.knowledge_ingestion import (
    KnowledgeIngestionService,
)


@pytest.mark.asyncio
async def test_ingests_document_into_database(
    tmp_path: Path,
) -> None:
    settings = get_settings()

    assert settings.test_database_url is not None

    source = tmp_path / (
        "webportal_ingestion_test.txt"
    )

    source.write_text(
        (
            "Login Page\n\n"
            "Enter username and password.\n\n"
            "Create New Project\n\n"
            "Enter the project owner title."
        ),
        encoding="utf-8",
    )

    engine = create_database_engine(
        settings.test_database_url
    )

    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
    )

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    try:
        async with session_factory() as session:
            storage = LocalDocumentStorage(
                tmp_path / "storage"
            )

            service = (
                KnowledgeIngestionService(
                    session,
                    storage=storage,
                )
            )

            result = await service.ingest(
                source
            )

            assert result.duplicate is False
            assert result.chunks_created >= 1

            document_result = (
                await session.execute(
                    select(
                        KnowledgeDocument
                    ).where(
                        KnowledgeDocument.id
                        == result.document_id
                    )
                )
            )

            document = (
                document_result
                .scalar_one()
            )

            assert document.status == "ready"

            version_result = (
                await session.execute(
                    select(
                        DocumentVersion
                    ).where(
                        DocumentVersion.id
                        == result.version_id
                    )
                )
            )

            version = (
                version_result.scalar_one()
            )

            assert version.version_number == 1

            chunk_result = (
                await session.execute(
                    select(
                        KnowledgeChunk
                    ).where(
                        KnowledgeChunk
                        .document_version_id
                        == result.version_id
                    )
                )
            )

            chunks = list(
                chunk_result.scalars()
            )

            assert len(chunks) >= 1

            await session.rollback()

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_duplicate_document_is_detected(
    tmp_path: Path,
) -> None:
    settings = get_settings()

    assert settings.test_database_url is not None

    source = tmp_path / (
        "webportal_duplicate_test.txt"
    )

    source.write_text(
        "WebPortal duplicate test.",
        encoding="utf-8",
    )

    engine = create_database_engine(
        settings.test_database_url
    )

    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
    )

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    try:
        async with session_factory() as session:
            storage = LocalDocumentStorage(
                tmp_path / "storage"
            )

            service = (
                KnowledgeIngestionService(
                    session,
                    storage=storage,
                )
            )

            first = await service.ingest(
                source
            )

            second = await service.ingest(
                source
            )

            assert first.duplicate is False
            assert second.duplicate is True

            assert (
                first.version_id
                == second.version_id
            )

            await session.rollback()

    finally:
        await engine.dispose()