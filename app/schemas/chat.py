from uuid import UUID

from pydantic import (
    BaseModel,
    Field,
    field_validator,
)


class ConversationCreatedResponse(
    BaseModel
):
    conversation_id: UUID
    status: str = "active"


class ChatMessageRequest(
    BaseModel
):
    message: str = Field(
        min_length=1,
        max_length=4000,
    )

    @field_validator("message")
    @classmethod
    def validate_message(
        cls,
        value: str,
    ) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError(
                "Message cannot be empty."
            )

        return normalized


class ChatSourceResponse(
    BaseModel
):
    section_title: str | None = None
    page_number: int | None = None


class ChatMessageResponse(
    BaseModel
):
    conversation_id: UUID
    answer: str

    sources: list[
        ChatSourceResponse
    ] = Field(
        default_factory=list
    )

class ConversationCreateRequest(BaseModel):
    # Browser metadata only. Never identity, permissions, or prompt context.
    model_config = {"extra": "forbid"}
    page_context: str | None = Field(
        default=None, min_length=1, max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$",
    )
