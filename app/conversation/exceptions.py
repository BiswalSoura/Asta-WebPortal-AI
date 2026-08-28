from uuid import UUID

from app.core.exceptions import AstaError


class ConversationError(AstaError):
    """Base exception for conversation operations."""


class ConversationNotFoundError(
    ConversationError
):
    def __init__(
        self,
        conversation_id: UUID,
    ) -> None:
        super().__init__(
            (
                "Conversation not found: "
                f"{conversation_id}"
            ),
            error_code=(
                "CONVERSATION_NOT_FOUND"
            ),
        )