from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.conversation import (
    ConversationNotFoundError,
)
from app.rag import RAGAnswer
from app.services.conversation_service import (
    ConversationService,
)


class FakeRepository:
    def __init__(self) -> None:
        self.conversation_id = uuid4()

        self.messages = []

    async def create_conversation(
        self,
        **kwargs,
    ):
        del kwargs

        return SimpleNamespace(
            id=self.conversation_id
        )

    async def get_conversation(
        self,
        conversation_id,
    ):
        if (
            conversation_id
            != self.conversation_id
        ):
            return None

        return SimpleNamespace(
            id=conversation_id
        )

    async def get_recent_messages(
        self,
        *,
        conversation_id,
        limit,
    ):
        del conversation_id, limit

        return list(self.messages)

    async def add_message(
        self,
        *,
        conversation_id,
        role,
        content,
        request_id=None,
        message_metadata=None,
    ):
        del conversation_id, request_id

        message = SimpleNamespace(
            role=role,
            content=content,
            message_metadata=(
                message_metadata
            ),
        )

        self.messages.append(message)

        return message


class FakeResponder:
    def __init__(self) -> None:
        self.question = None

    async def ask(
        self,
        question: str,
    ) -> RAGAnswer:
        self.question = question

        return RAGAnswer(
            answer="Grounded response.",
            sources=(),
            model="fake-model",
            prompt_tokens=1,
            completion_tokens=1,
            total_tokens=2,
            grounded=True,
        )


@pytest.mark.asyncio
async def test_start_conversation_returns_id() -> None:
    repository = FakeRepository()

    service = ConversationService(
        session=None,
        repository=repository,
        responder=FakeResponder(),
    )

    conversation_id = (
        await service.start_conversation()
    )

    assert (
        conversation_id
        == repository.conversation_id
    )


@pytest.mark.asyncio
async def test_send_message_persists_user_and_assistant() -> None:
    repository = FakeRepository()

    responder = FakeResponder()

    service = ConversationService(
        session=None,
        repository=repository,
        responder=responder,
    )

    result = await service.send_message(
        conversation_id=(
            repository.conversation_id
        ),
        message=(
            "How does Create New Project work?"
        ),
    )

    assert len(repository.messages) == 2

    assert (
        repository.messages[0].role
        == "user"
    )

    assert (
        repository.messages[1].role
        == "assistant"
    )

    assert (
        result.answer.answer
        == "Grounded response."
    )


@pytest.mark.asyncio
async def test_missing_conversation_is_rejected() -> None:
    repository = FakeRepository()

    service = ConversationService(
        session=None,
        repository=repository,
        responder=FakeResponder(),
    )

    with pytest.raises(
        ConversationNotFoundError
    ):
        await service.send_message(
            conversation_id=uuid4(),
            message="Hello",
        )