from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.guardrails import GuardrailService
from app.llm import create_llm_client
from app.rag import (
    RAGAnswer,
    RAGService,
)
from app.services.knowledge_retrieval import (
    KnowledgeRetrievalService,
)


class RAGAnsweringService(Protocol):
    async def answer(
        self,
        question: str,
    ) -> RAGAnswer:
        ...


class AstaService:
    def __init__(
        self,
        session: AsyncSession | None = None,
        *,
        guardrail_service: (
            GuardrailService | None
        ) = None,
        rag_service: (
            RAGAnsweringService | None
        ) = None,
    ) -> None:
        self.guardrail_service = (
            guardrail_service
            or GuardrailService()
        )

        if rag_service is not None:
            self.rag_service = rag_service
            return

        if session is None:
            raise ValueError(
                (
                    "A database session is required "
                    "when rag_service is not provided."
                )
            )

        retrieval_service = (
            KnowledgeRetrievalService(
                session
            )
        )

        llm_client = create_llm_client()

        self.rag_service = RAGService(
            retrieval_service=(
                retrieval_service
            ),
            llm_client=llm_client,
        )

    async def ask(
        self,
        question: str,
    ) -> RAGAnswer:
        decision = (
            self.guardrail_service
            .evaluate(question)
        )

        if not decision.allowed:
            return RAGAnswer(
                answer=(
                    decision.response
                    or "I can help with WebPortal."
                ),
                sources=(),
                model=None,
                prompt_tokens=None,
                completion_tokens=None,
                total_tokens=None,
                grounded=False,
            )

        return await self.rag_service.answer(
            question
        )