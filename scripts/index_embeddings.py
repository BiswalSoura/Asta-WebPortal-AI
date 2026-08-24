import asyncio
import sys

from app.database.session import (
    get_session_factory,
)
from app.services import (
    EmbeddingIndexingService,
)


async def index_embeddings() -> None:
    session_factory = (
        get_session_factory()
    )

    total_indexed = 0
    model_name: str | None = None
    dimensions: int | None = None

    async with session_factory() as session:
        service = EmbeddingIndexingService(
            session
        )

        try:
            while True:
                result = (
                    await service.index_batch()
                )

                model_name = result.model_name
                dimensions = result.dimensions

                if result.indexed_chunks == 0:
                    break

                await session.commit()

                total_indexed += (
                    result.indexed_chunks
                )

        except Exception:
            await session.rollback()
            raise

    print(
        "Embedding indexing completed successfully."
    )

    print(
        f"Model: {model_name}"
    )

    print(
        f"Dimensions: {dimensions}"
    )

    print(
        f"Chunks indexed: {total_indexed}"
    )


def main() -> None:
    if sys.platform == "win32":
        asyncio.run(
            index_embeddings(),
            loop_factory=asyncio.SelectorEventLoop,
        )

    else:
        asyncio.run(
            index_embeddings()
        )


if __name__ == "__main__":
    main()