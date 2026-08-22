import argparse
import asyncio
import sys
from pathlib import Path

from app.database.session import (
    get_session_factory,
)
from app.services import (
    KnowledgeIngestionService,
)


async def ingest_document(
    document_path: Path,
) -> None:
    session_factory = (
        get_session_factory()
    )

    async with session_factory() as session:
        service = KnowledgeIngestionService(
            session
        )

        try:
            result = await service.ingest(
                document_path
            )

            await session.commit()

        except Exception:
            await session.rollback()
            raise

    print(
        "Ingestion completed successfully."
    )

    print(
        f"Document ID: {result.document_id}"
    )

    print(
        f"Version: {result.version_number}"
    )

    print(
        f"Chunks created: {result.chunks_created}"
    )

    print(
        f"Duplicate: {result.duplicate}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Ingest a WebPortal knowledge document "
            "into Asta."
        )
    )

    parser.add_argument(
        "document",
        type=Path,
        help="Path to the document to ingest.",
    )

    arguments = parser.parse_args()

    if sys.platform == "win32":
        asyncio.run(
            ingest_document(
                arguments.document
            ),
            loop_factory=asyncio.SelectorEventLoop,
        )

    else:
        asyncio.run(
            ingest_document(
                arguments.document
            )
        )


if __name__ == "__main__":
    main()