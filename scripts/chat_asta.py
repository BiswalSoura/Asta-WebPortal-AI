import argparse
import asyncio
import sys
from uuid import UUID

from app.database.session import (
    get_session_factory,
)
from app.services import (
    ConversationService,
)


async def chat(
    conversation_id: UUID | None,
) -> None:
    session_factory = (
        get_session_factory()
    )

    async with session_factory() as session:
        service = ConversationService(
            session
        )

        if conversation_id is None:
            conversation_id = (
                await service
                .start_conversation()
            )

            await session.commit()

        print()
        print(
            f"Conversation ID: "
            f"{conversation_id}"
        )

        print(
            "Type /exit to end the chat."
        )

        print()

        while True:
            message = input("You: ").strip()

            if message.lower() in {
                "/exit",
                "/quit",
            }:
                break

            if not message:
                continue

            try:
                result = (
                    await service
                    .send_message(
                        conversation_id=(
                            conversation_id
                        ),
                        message=message,
                    )
                )

                await session.commit()

            except Exception:
                await session.rollback()
                raise

            print()
            print("Asta:")
            print(
                result.answer.answer
            )

            if result.contextualized:
                print()
                print(
                    "[Conversation context used]"
                )

            print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Start or resume an Asta "
            "conversation."
        )
    )

    parser.add_argument(
        "--conversation-id",
        type=UUID,
        default=None,
        help=(
            "Existing conversation UUID "
            "to resume."
        ),
    )

    arguments = parser.parse_args()

    if sys.platform == "win32":
        asyncio.run(
            chat(
                arguments.conversation_id
            ),
            loop_factory=(
                asyncio.SelectorEventLoop
            ),
        )

    else:
        asyncio.run(
            chat(
                arguments.conversation_id
            )
        )


if __name__ == "__main__":
    main()