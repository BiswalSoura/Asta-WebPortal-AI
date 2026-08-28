import pytest

from app.guardrails import GuardrailService
from app.rag import RAGAnswer
from app.services.asta_service import (
    AstaService,
)


class FakeRAGService:
    def __init__(self) -> None:
        self.called = False

    async def answer(
        self,
        question: str,
    ) -> RAGAnswer:
        self.called = True

        return RAGAnswer(
            answer=(
                f"Grounded answer for: {question}"
            ),
            sources=(),
            model="fake-model",
            prompt_tokens=1,
            completion_tokens=1,
            total_tokens=2,
            grounded=True,
        )


@pytest.mark.asyncio
async def test_off_topic_does_not_reach_rag() -> None:
    rag = FakeRAGService()

    service = AstaService(
        guardrail_service=(
            GuardrailService()
        ),
        rag_service=rag,
    )

    result = await service.ask(
        "Tell me a joke."
    )

    assert rag.called is False
    assert result.model is None
    assert result.grounded is False


@pytest.mark.asyncio
async def test_webportal_question_reaches_rag() -> None:
    rag = FakeRAGService()

    service = AstaService(
        guardrail_service=(
            GuardrailService()
        ),
        rag_service=rag,
    )

    result = await service.ask(
        "How does Create New Project work?"
    )

    assert rag.called is True
    assert result.model == "fake-model"
    assert result.grounded is True