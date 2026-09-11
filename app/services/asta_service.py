from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.telemetry import emit, observe
from app.intent.query_understanding import CLARIFICATION_RESPONSE, normalize_language
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
            emit("chat_outcome", path="guardrail_bypass", outcome="bypass",
                 grounded=False, model_used=False, source_count=0)
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

        # Raw security checks above always precede language interpretation.
        contextual = question.startswith("RECENT CONVERSATION CONTEXT:\n")
        understood = normalize_language(question) if not contextual else None
        query = understood.query if understood else question
        normalized_decision = self.guardrail_service.evaluate(query)
        if not normalized_decision.allowed or (understood and understood.clarification):
            clarification = normalized_decision.allowed
            emit("chat_outcome", path="guardrail_bypass", outcome="bypass",
                 query_understanding="clarification" if clarification else "normalized",
                 grounded=False, model_used=False, source_count=0)
            return RAGAnswer(
                answer=CLARIFICATION_RESPONSE if clarification else normalized_decision.response,
                sources=(), model=None, prompt_tokens=None, completion_tokens=None,
                total_tokens=None, grounded=False,
            )
        with observe("rag"):
            result = await self.rag_service.answer(query)
        emit("chat_outcome", path="rag",
             outcome="grounded" if result.grounded else "insufficient_information",
             grounded=result.grounded, model_used=result.model is not None,
             source_count=len(result.sources))
        return result
