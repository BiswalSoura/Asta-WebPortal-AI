import argparse
import asyncio
import sys

from app.database.session import (
    get_session_factory,
)
from app.services import AstaService


async def ask_asta(
    question: str,
) -> None:
    session_factory = (
        get_session_factory()
    )

    async with session_factory() as session:
        service = AstaService(
            session
        )

        result = await service.ask(
            question
        )

    print()
    print("Asta:")
    print(result.answer)

    print()

    if result.sources:
        print("Sources:")

        for index, source in enumerate(
            result.sources,
            start=1,
        ):
            print(
                (
                    f"{index}. "
                    f"{source.original_filename}"
                    f" | Section: "
                    f"{source.section_title}"
                )
            )

    if result.model is not None:
        print()
        print(
            f"Model: {result.model}"
        )

        print(
            f"Tokens: {result.total_tokens}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Ask Asta a grounded "
            "WebPortal question."
        )
    )

    parser.add_argument(
        "question",
        type=str,
        help="Question for Asta.",
    )

    arguments = parser.parse_args()

    if sys.platform == "win32":
        asyncio.run(
            ask_asta(
                arguments.question
            ),
            loop_factory=(
                asyncio.SelectorEventLoop
            ),
        )

    else:
        asyncio.run(
            ask_asta(
                arguments.question
            )
        )


if __name__ == "__main__":
    main()