from uuid import uuid4

import pytest

from app.llm.models import LLMResponse
from app.rag.rag_service import (
    INSUFFICIENT_KNOWLEDGE_RESPONSE,
    RAGService,
)
from app.retrieval.models import (
    RetrievalCandidate,
)


class FakeRetrievalService:
    async def search(
        self,
        query: str,
    ):
        assert query == (
            "How do I create a project?"
        )

        return [
            RetrievalCandidate(
                chunk_id=uuid4(),
                document_id=uuid4(),
                document_name=(
                    "WebPortal Guide"
                ),
                original_filename=(
                    "webportal-guide.md"
                ),
                content=(
                    "The Create New Project "
                    "page starts a new project."
                ),
                section_title=(
                    "Create New Project"
                ),
                page_number=None,
                source_metadata={},
                vector_score=0.9,
                rerank_score=0.95,
            )
        ]


class EmptyRetrievalService:
    async def search(
        self,
        query: str,
    ):
        del query
        return []


class FakeLLMClient:
    def __init__(self) -> None:
        self.called = False

    async def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> LLMResponse:
        self.called = True

        assert "Asta" in system_prompt

        assert (
            "Create New Project"
            in user_prompt
        )

        return LLMResponse(
            content=(
                "Use the Create New Project page."
            ),
            model="fake-model",
            prompt_tokens=20,
            completion_tokens=7,
            total_tokens=27,
        )


@pytest.mark.asyncio
async def test_rag_service_generates_grounded_answer() -> None:
    llm = FakeLLMClient()

    service = RAGService(
        retrieval_service=(
            FakeRetrievalService()
        ),
        llm_client=llm,
    )

    result = await service.answer(
        "How do I create a project?"
    )

    assert result.grounded is True

    assert result.answer == (
        "Use the Create New Project page."
    )

    assert len(result.sources) == 1

    assert llm.called is True


@pytest.mark.asyncio
async def test_rag_service_skips_llm_without_evidence() -> None:
    llm = FakeLLMClient()

    service = RAGService(
        retrieval_service=(
            EmptyRetrievalService()
        ),
        llm_client=llm,
    )

    result = await service.answer(
        "Unsupported question"
    )

    assert result.grounded is False

    assert result.answer == (
        INSUFFICIENT_KNOWLEDGE_RESPONSE
    )

    assert result.sources == ()

    assert llm.called is False