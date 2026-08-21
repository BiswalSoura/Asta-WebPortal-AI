import asyncio
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import get_settings
from app.database.base import Base

# Import all database models so SQLAlchemy metadata is populated
# before Alembic performs autogeneration.
import app.database.models  # noqa: F401


config = context.config


if config.config_file_name is not None:
    fileConfig(config.config_file_name)


settings = get_settings()


database_url = (
    os.getenv("ALEMBIC_DATABASE_URL")
    or settings.database_url
)


if not database_url:
    raise RuntimeError(
        "Database URL is required for Alembic migrations."
    )


config.set_main_option(
    "sqlalchemy.url",
    database_url.replace("%", "%%"),
)


target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={
            "paramstyle": "named",
        },
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    configuration = config.get_section(
        config.config_ini_section,
        {},
    )

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(
            do_run_migrations,
        )

    await connectable.dispose()


def run_migrations_online() -> None:
    if sys.platform == "win32":
        asyncio.run(
            run_async_migrations(),
            loop_factory=asyncio.SelectorEventLoop,
        )
    else:
        asyncio.run(
            run_async_migrations(),
        )


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()