from functools import lru_cache

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.database import (
    get_database_session,
)
from app.core.config import get_settings
from app.embeddings import EmbeddingService
from app.llm import (
    LLMClient,
    create_llm_client,
)
from app.rag import RAGService
from app.retrieval import (
    CrossEncoderReranker,
)
from app.services import (
    AstaService,
    ConversationService,
    KnowledgeRetrievalService,
)


@lru_cache(maxsize=1)
def get_shared_embedding_service(
) -> EmbeddingService:
    settings = get_settings()

    return EmbeddingService(
        model_name=settings.embedding_model,
        device=settings.embedding_device,
        batch_size=(
            settings.embedding_batch_size
        ),
    )


@lru_cache(maxsize=1)
def get_shared_reranker(
) -> CrossEncoderReranker:
    settings = get_settings()

    return CrossEncoderReranker(
        model_name=settings.reranker_model,
        device=settings.reranker_device,
    )


@lru_cache(maxsize=1)
def get_shared_llm_client(
) -> LLMClient:
    return create_llm_client()


def get_conversation_service(
    session: AsyncSession = Depends(
        get_database_session
    ),
) -> ConversationService:
    retrieval_service = (
        KnowledgeRetrievalService(
            session,
            embedding_service=(
                get_shared_embedding_service()
            ),
            reranker=(
                get_shared_reranker()
            ),
        )
    )

    rag_service = RAGService(
        retrieval_service=retrieval_service,
        llm_client=get_shared_llm_client(),
    )

    asta_service = AstaService(
        rag_service=rag_service,
    )

    return ConversationService(
        session,
        responder=asta_service,
    )