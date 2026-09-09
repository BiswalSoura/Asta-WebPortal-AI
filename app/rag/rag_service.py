from app.llm import LLMClient
from app.prompts import ASTA_SYSTEM_PROMPT
from app.rag.context_builder import (
    RAGContextBuilder,
)
from app.rag.models import (
    RAGAnswer,
    RAGSource,
)
from app.rag.prompt_builder import (
    RAGPromptBuilder,
)
from app.services.knowledge_retrieval import (
    KnowledgeRetrievalService,
)

from app.rag.grounding_sanitizer import (
    GroundingSanitizer,
)

INSUFFICIENT_KNOWLEDGE_RESPONSE = (
    "I don't currently have enough approved "
    "WebPortal information to answer that "
    "accurately."
)


class RAGService:
    def __init__(
        self,
        *,
        retrieval_service: (
            KnowledgeRetrievalService
        ),
        llm_client: LLMClient,
        context_builder: (
            RAGContextBuilder | None
        ) = None,
        prompt_builder: (
            RAGPromptBuilder | None
        ) = None,
        grounding_sanitizer: (
            GroundingSanitizer | None
        ) = None,
    ) -> None:
        self.retrieval_service = (
            retrieval_service
        )

        self.llm_client = llm_client

        self.context_builder = (
            context_builder
            or RAGContextBuilder()
        )

        self.prompt_builder = (
            prompt_builder
            or RAGPromptBuilder()
        )

        self.grounding_sanitizer = (
            grounding_sanitizer
            or GroundingSanitizer()
        )

    async def answer(
        self,
        question: str,
    ) -> RAGAnswer:
        candidates = (
            await self.retrieval_service
            .search(question)
        )

        if not candidates:
            return RAGAnswer(
                answer=(
                    INSUFFICIENT_KNOWLEDGE_RESPONSE
                ),
                sources=(),
                model=None,
                prompt_tokens=None,
                completion_tokens=None,
                total_tokens=None,
                grounded=False,
            )

        context = (
            self.context_builder
            .build(candidates)
        )

        user_prompt = (
            self.prompt_builder.build(
                question=question,
                context=context,
            )
        )

        response = (
            await self.llm_client.generate(
                system_prompt=(
                    ASTA_SYSTEM_PROMPT
                ),
                user_prompt=user_prompt,
            )
        )

        sanitized_answer = (
            self.grounding_sanitizer
            .sanitize(
                answer=response.content,
                context=context,
            )
        )

        sources = tuple(
            RAGSource(
                document_name=(
                    candidate.document_name
                ),
                original_filename=(
                    candidate
                    .original_filename
                ),
                section_title=(
                    candidate.section_title
                ),
                page_number=(
                    candidate.page_number
                ),
                vector_score=(
                    candidate.vector_score
                ),
                rerank_score=(
                    candidate.rerank_score
                ),
            )
            for candidate in candidates
        )

        return RAGAnswer(
            answer=sanitized_answer,
            sources=sources,
            model=response.model,
            prompt_tokens=(
                response.prompt_tokens
            ),
            completion_tokens=(
                response.completion_tokens
            ),
            total_tokens=(
                response.total_tokens
            ),
            grounded=True,
        )