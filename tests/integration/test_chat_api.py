from uuid import uuid4

import pytest
from httpx import (
    ASGITransport,
    AsyncClient,
)

from app.api.dependencies import (
    get_conversation_service,
    get_database_session,
)
from app.conversation import (
    ConversationNotFoundError,
    ConversationReply,
)
from app.main import app
from app.rag import (
    RAGAnswer,
    RAGSource,
)


class FakeSession:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


class FakeConversationService:
    def __init__(self) -> None:
        self.conversation_id = uuid4()

    async def start_conversation(
        self,
    ):
        return self.conversation_id

    async def send_message(
        self,
        *,
        conversation_id,
        message,
        request_id=None,
    ):
        del request_id

        if (
            conversation_id
            != self.conversation_id
        ):
            raise ConversationNotFoundError(
                conversation_id
            )

        assert message

        return ConversationReply(
            conversation_id=(
                conversation_id
            ),
            contextualized=False,
            answer=RAGAnswer(
                answer=(
                    "Use the Create New Project page."
                ),
                sources=(
                    RAGSource(
                        document_name=(
                            "WebPortal Guide"
                        ),
                        original_filename=(
                            "webportal-guide.md"
                        ),
                        section_title=(
                            "Create New Project"
                        ),
                        page_number=None,
                        vector_score=0.9,
                        rerank_score=0.95,
                    ),
                ),
                model="internal-model",
                prompt_tokens=10,
                completion_tokens=5,
                total_tokens=15,
                grounded=True,
            ),
        )


async def _override_session():
    yield FakeSession()


@pytest.mark.asyncio
async def test_create_conversation_endpoint() -> None:
    service = FakeConversationService()

    app.dependency_overrides[
        get_database_session
    ] = _override_session

    app.dependency_overrides[
        get_conversation_service
    ] = lambda: service

    try:
        transport = ASGITransport(
            app=app
        )

        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/v1/chat/conversations"
            )

        assert response.status_code == 201

        payload = response.json()

        assert payload[
            "conversation_id"
        ] == str(
            service.conversation_id
        )

        assert payload["status"] == "active"

    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_send_message_endpoint() -> None:
    service = FakeConversationService()

    app.dependency_overrides[
        get_database_session
    ] = _override_session

    app.dependency_overrides[
        get_conversation_service
    ] = lambda: service

    try:
        transport = ASGITransport(
            app=app
        )

        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            response = await client.post(
                (
                    "/api/v1/chat/conversations/"
                    f"{service.conversation_id}"
                    "/messages"
                ),
                json={
                    "message": (
                        "How do I create a project?"
                    )
                },
            )

        assert response.status_code == 200

        payload = response.json()

        assert payload["answer"] == (
            "Use the Create New Project page."
        )

        assert (
            payload["sources"][0]
            ["section_title"]
            == "Create New Project"
        )

        assert "model" not in payload
        assert "total_tokens" not in payload

    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_empty_message_is_rejected() -> None:
    service = FakeConversationService()

    app.dependency_overrides[
        get_database_session
    ] = _override_session

    app.dependency_overrides[
        get_conversation_service
    ] = lambda: service

    try:
        transport = ASGITransport(
            app=app
        )

        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            response = await client.post(
                (
                    "/api/v1/chat/conversations/"
                    f"{service.conversation_id}"
                    "/messages"
                ),
                json={
                    "message": "   "
                },
            )

        assert response.status_code == 422

    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_unknown_conversation_returns_404() -> None:
    service = FakeConversationService()

    app.dependency_overrides[
        get_database_session
    ] = _override_session

    app.dependency_overrides[
        get_conversation_service
    ] = lambda: service

    try:
        transport = ASGITransport(
            app=app
        )

        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            response = await client.post(
                (
                    "/api/v1/chat/conversations/"
                    f"{uuid4()}"
                    "/messages"
                ),
                json={
                    "message": "Hello"
                },
            )

        assert response.status_code == 404

        assert response.json() == {
            "detail": (
                "Conversation was not found."
            )
        }

    finally:
        app.dependency_overrides.clear()