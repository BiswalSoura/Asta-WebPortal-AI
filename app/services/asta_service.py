from sqlalchemy.ext.asyncio import AsyncSession

from app.llm import create_llm_client
from app.rag import RAGAnswer, RAGService
from app.services.knowledge_retrieval import (
    KnowledgeRetrievalService,
)


class AstaService:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
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
        return await self.rag_service.answer(
            question
        )