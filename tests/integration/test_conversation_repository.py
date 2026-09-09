import pytest
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from app.core.config import get_settings
from app.database.repositories import (
    ConversationRepository,
)
from app.database.session import (
    create_database_engine,
)


@pytest.mark.asyncio
async def test_conversation_messages_are_persisted_in_order() -> None:
    settings = get_settings()

    assert (
        settings.test_database_url
        is not None
    )

    engine = create_database_engine(
        settings.test_database_url
    )

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    try:
        async with session_factory() as session:
            repository = (
                ConversationRepository(
                    session
                )
            )

            conversation = (
                await repository
                .create_conversation()
            )

            await repository.add_message(
                conversation_id=(
                    conversation.id
                ),
                role="user",
                content="First question",
            )

            await repository.add_message(
                conversation_id=(
                    conversation.id
                ),
                role="assistant",
                content="First answer",
            )

            messages = (
                await repository
                .get_recent_messages(
                    conversation_id=(
                        conversation.id
                    ),
                    limit=6,
                )
            )

            assert len(messages) == 2

            assert (
                messages[0].content
                == "First question"
            )

            assert (
                messages[1].content
                == "First answer"
            )

            await session.rollback()

    finally:
        await engine.dispose()