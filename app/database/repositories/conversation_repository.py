from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from app.database.models import (
    Conversation,
    Message,
)


class ConversationRepository:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    async def create_conversation(
        self,
        *,
        user_role: str | None = None,
        page_context: dict | None = None,
        permission_context: (
            dict | None
        ) = None,
    ) -> Conversation:
        conversation = Conversation(
            status="active",
            user_role=user_role,
            page_context=page_context,
            permission_context=(
                permission_context
            ),
        )

        self.session.add(conversation)

        await self.session.flush()

        return conversation

    async def get_conversation(
        self,
        conversation_id: UUID,
    ) -> Conversation | None:
        result = await self.session.execute(
            select(Conversation).where(
                Conversation.id
                == conversation_id
            )
        )

        return result.scalar_one_or_none()

    async def add_message(
        self,
        *,
        conversation_id: UUID,
        role: str,
        content: str,
        request_id: str | None = None,
        message_metadata: (
            dict | None
        ) = None,
    ) -> Message:
        # Serialize timestamp allocation across writers to this conversation.
        # Wall-clock values may repeat (or move backwards), especially on Windows.
        await self.session.execute(
            select(Conversation.id)
            .where(Conversation.id == conversation_id)
            .with_for_update()
        )
        latest = await self.session.scalar(
            select(Message.created_at)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        created_at = datetime.now(timezone.utc)
        if latest is not None and created_at <= latest:
            created_at = latest + timedelta(microseconds=1)

        message = Message(
            conversation_id=(
                conversation_id
            ),
            role=role,
            content=content,
            request_id=request_id,
            message_metadata=(
                message_metadata
            ),
            created_at=created_at,
        )

        self.session.add(message)

        await self.session.flush()

        return message

    async def get_recent_messages(
        self,
        *,
        conversation_id: UUID,
        limit: int,
    ) -> list[Message]:
        result = await self.session.execute(
            select(Message)
            .where(
                Message.conversation_id
                == conversation_id
            )
            .order_by(
                Message.created_at.desc()
            )
            .limit(limit)
        )

        messages = list(
            result.scalars().all()
        )

        messages.reverse()

        return messages
