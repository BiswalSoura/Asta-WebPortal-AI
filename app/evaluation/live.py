"""Compose the existing pipeline and a rollback-only database conversation scope."""

import hashlib
import json
from contextlib import asynccontextmanager

from sqlalchemy import select

from app.api.dependencies.services import (
    get_shared_embedding_service,
    get_shared_llm_client,
    get_shared_reranker,
)
from app.database.models import ChunkEmbedding, DocumentVersion, KnowledgeChunk, KnowledgeDocument
from app.database.repositories import ConversationRepository
from app.rag import RAGService
from app.services import AstaService, ConversationService, KnowledgeRetrievalService
from app.evaluation.runner import CallCounter, EvaluationServices


@asynccontextmanager
async def isolated_conversation(session, responder):
    """Exercise SQL persistence/history without committing evaluation records."""
    transaction = await session.begin_nested()
    conversation_id = None
    try:
        conversation = ConversationService(session, responder=responder)
        conversation_id = await conversation.start_conversation(
            page_context={"evaluation": "M12", "persistence": "rollback-only"})
        yield conversation, conversation_id
    finally:
        await transaction.rollback()
        if conversation_id is not None:
            existing = await ConversationRepository(session).get_conversation(conversation_id)
            if existing is not None:
                raise RuntimeError("Evaluation cleanup failed")


def build_services(session) -> EvaluationServices:
    retrieval = CallCounter(KnowledgeRetrievalService(
        session, embedding_service=get_shared_embedding_service(),
        reranker=get_shared_reranker()), "search")
    llm = CallCounter(get_shared_llm_client(), "generate")
    rag = CallCounter(RAGService(retrieval_service=retrieval, llm_client=llm), "answer")
    asta = AstaService(rag_service=rag)

    return EvaluationServices(retrieval, rag, llm, asta,
                              lambda: isolated_conversation(session, asta))


async def corpus_manifest(session):
    rows = (await session.execute(
        select(KnowledgeChunk.id, KnowledgeChunk.section_title, KnowledgeChunk.content,
               DocumentVersion.content_hash, ChunkEmbedding.model_name)
        .join(ChunkEmbedding, ChunkEmbedding.chunk_id == KnowledgeChunk.id)
        .join(DocumentVersion, DocumentVersion.id == KnowledgeChunk.document_version_id)
        .join(KnowledgeDocument, KnowledgeDocument.id == DocumentVersion.document_id)
        .where(DocumentVersion.is_active.is_(True), KnowledgeDocument.status == "ready")
        .order_by(KnowledgeChunk.id)
    )).all()
    sections = {}
    fingerprint = []
    for chunk_id, section, content, content_hash, model in rows:
        sections[section or "[untitled]"] = sections.get(section or "[untitled]", 0) + 1
        fingerprint.append([str(chunk_id), section, content, content_hash, model])
    digest = hashlib.sha256(json.dumps(fingerprint, ensure_ascii=False).encode()).hexdigest()
    return sections, digest
