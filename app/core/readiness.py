"""Bounded database capability probe; no model or provider dependencies."""
import asyncio
from dataclasses import dataclass

from sqlalchemy import text

from app.database.session import get_engine


@dataclass(frozen=True)
class Readiness:
    database: bool = False
    pgvector: bool = False

    @property
    def ready(self):
        return self.database and self.pgvector

    def components(self):
        return {"database": "ready" if self.database else "unavailable",
                "pgvector": "ready" if self.pgvector else "unavailable"}


async def check_readiness(engine=None) -> Readiness:
    database = False
    try:
        async with asyncio.timeout(5):
            engine = engine if engine is not None else get_engine()
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
                database = True
                vector = await connection.scalar(text(
                    "SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')"
                ))
                return Readiness(database=True, pgvector=bool(vector))
    except Exception:
        return Readiness(database=database)
