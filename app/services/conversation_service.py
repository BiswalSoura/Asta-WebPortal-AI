from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from app.core.telemetry import emit
from app.conversation import (
    ConversationContextBuilder,
    ConversationHistoryMessage,
    ConversationNotFoundError,
    ConversationReply,
)
from app.core.config import get_settings
from app.database.repositories import (
    ConversationRepository,
)
from app.rag import RAGAnswer
from app.services.asta_service import (
    AstaService,
)


class AstaResponder(Protocol):
    async def ask(
        self,
        question: str,
    ) -> RAGAnswer:
        ...


class ConversationService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        responder: (
            AstaResponder | None
        ) = None,
        repository: (
            ConversationRepository | None
        ) = None,
        context_builder: (
            ConversationContextBuilder
            | None
        ) = None,
    ) -> None:
        settings = get_settings()

        self.repository = (
            repository
            or ConversationRepository(
                session
            )
        )

        self.responder = (
            responder
            or AstaService(session)
        )

        self.context_builder = (
            context_builder
            or ConversationContextBuilder(
                max_chars=(
                    settings
                    .conversation_context_max_chars
                )
            )
        )

        self.history_limit = (
            settings
            .conversation_history_messages
        )

    async def start_conversation(
        self,
        *,
        user_role: str | None = None,
        page_context: dict | None = None,
        permission_context: (
            dict | None
        ) = None,
    ) -> UUID:
        conversation = (
            await self.repository
            .create_conversation(
                user_role=user_role,
                page_context=page_context,
                permission_context=(
                    permission_context
                ),
            )
        )

        return conversation.id

    async def send_message(
        self,
        *,
        conversation_id: UUID,
        message: str,
        request_id: str | None = None,
    ) -> ConversationReply:
        conversation = (
            await self.repository
            .get_conversation(
                conversation_id
            )
        )

        if conversation is None:
            raise ConversationNotFoundError(
                conversation_id
            )

        stored_history = (
            await self.repository
            .get_recent_messages(
                conversation_id=(
                    conversation_id
                ),
                limit=self.history_limit,
            )
        )

        history = [
            ConversationHistoryMessage(
                role=item.role,
                content=item.content,
            )
            for item in stored_history
        ]

        (
            query,
            contextualized,
        ) = self.context_builder.build_query(
            current_message=message,
            history=history,
        )

        await self.repository.add_message(
            conversation_id=conversation_id,
            role="user",
            content=message.strip(),
            request_id=request_id,
        )

        answer = await self.responder.ask(
            query
        )

        assistant_metadata = {
            "grounded": answer.grounded,
            "model": answer.model,
            "source_count": len(
                answer.sources
            ),
            "contextualized": contextualized,
        }

        await self.repository.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=answer.answer,
            request_id=request_id,
            message_metadata=(
                assistant_metadata
            ),
        )

        emit("conversation_outcome", request_id=request_id,
             contextualized=contextualized, grounded=answer.grounded,
             model_used=answer.model is not None, source_count=len(answer.sources))

        return ConversationReply(
            conversation_id=conversation_id,
            answer=answer,
            contextualized=contextualized,
        )
