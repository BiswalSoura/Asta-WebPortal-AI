import pytest
from sqlalchemy import text

from app.core.config import get_settings
from app.database.session import create_database_engine


@pytest.mark.asyncio
async def test_database_connection() -> None:
    settings = get_settings()

    assert settings.test_database_url is not None

    engine = create_database_engine(
        settings.test_database_url,
    )

    try:
        async with engine.connect() as connection:
            result = await connection.execute(
                text(
                    "SELECT current_user, current_database()"
                )
            )

            row = result.one()

            assert row[0] == "asta_app"
            assert row[1] == "asta_test_db"

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_pgvector_extension_available() -> None:
    settings = get_settings()

    assert settings.test_database_url is not None

    engine = create_database_engine(
        settings.test_database_url,
    )

    try:
        async with engine.connect() as connection:
            result = await connection.execute(
                text(
                    """
                    SELECT extversion
                    FROM pg_extension
                    WHERE extname = 'vector'
                    """
                )
            )

            version = result.scalar_one()

            assert version == "0.8.6"

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_expected_tables_exist() -> None:
    settings = get_settings()

    assert settings.test_database_url is not None

    engine = create_database_engine(
        settings.test_database_url,
    )

    expected_tables = {
        "alembic_version",
        "chunk_embeddings",
        "conversations",
        "document_versions",
        "feedback",
        "ingestion_jobs",
        "knowledge_chunks",
        "knowledge_documents",
        "messages",
    }

    try:
        async with engine.connect() as connection:
            result = await connection.execute(
                text(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    """
                )
            )

            actual_tables = {
                row[0]
                for row in result.fetchall()
            }

            assert expected_tables.issubset(
                actual_tables
            )

    finally:
        await engine.dispose()