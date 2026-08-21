from functools import lru_cache

from pgvector.psycopg import register_vector_async
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings
from app.core.exceptions import ConfigurationError


def create_database_engine(database_url: str) -> AsyncEngine:
    engine = create_async_engine(
        database_url,
        pool_pre_ping=True,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def register_pgvector(
        dbapi_connection,
        connection_record,
    ) -> None:
        del connection_record
        dbapi_connection.run_async(register_vector_async)

    return engine


@lru_cache
def get_engine() -> AsyncEngine:
    settings = get_settings()

    if not settings.database_url:
        raise ConfigurationError(
            "DATABASE_URL is not configured."
        )

    return create_database_engine(
        settings.database_url,
    )


@lru_cache
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )