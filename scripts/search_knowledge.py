import argparse
import asyncio
import sys

from app.database.session import (
    get_session_factory,
)
from app.services import (
    KnowledgeRetrievalService,
)


async def search_knowledge(
    query: str,
) -> None:
    session_factory = (
        get_session_factory()
    )

    async with session_factory() as session:
        service = KnowledgeRetrievalService(
            session
        )

        results = await service.search(
            query
        )

    if not results:
        print(
            "No relevant WebPortal knowledge found."
        )

        return

    print(
        f"Retrieved {len(results)} result(s)."
    )

    print()

    for rank, result in enumerate(
        results,
        start=1,
    ):
        preview = (
            result.content
            .replace("\n", " ")
            [:300]
        )

        print(
            f"Rank: {rank}"
        )

        print(
            f"Document: "
            f"{result.original_filename}"
        )

        print(
            f"Section: "
            f"{result.section_title}"
        )

        print(
            f"Page: {result.page_number}"
        )

        print(
            f"Vector score: "
            f"{result.vector_score:.4f}"
        )

        print(
            f"Rerank score: "
            f"{result.rerank_score:.4f}"
        )

        print(
            f"Content: {preview}"
        )

        print("-" * 80)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Search Asta's indexed "
            "WebPortal knowledge."
        )
    )

    parser.add_argument(
        "query",
        type=str,
        help="WebPortal question to search.",
    )

    arguments = parser.parse_args()

    if sys.platform == "win32":
        asyncio.run(
            search_knowledge(
                arguments.query
            ),
            loop_factory=(
                asyncio.SelectorEventLoop
            ),
        )

    else:
        asyncio.run(
            search_knowledge(
                arguments.query
            )
        )


if __name__ == "__main__":
    main()