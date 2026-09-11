from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import get_settings
from app.database.session import create_database_engine
from app.database.models import DocumentVersion, KnowledgeChunk, ChunkEmbedding, KnowledgeDocument
from app.database.models.conversation import Conversation, Message, Feedback
from app.services.document_storage import LocalDocumentStorage
from app.services.knowledge_operations import KnowledgeOperations, OperationsError
from app.services.feedback_service import record_feedback


class Embeddings:
    model_name = 'BAAI/bge-small-en-v1.5'
    def embed_documents(self, texts):
        return [[1.0] + [0.0]*383 for text in texts]


@pytest_asyncio.fixture
async def db(tmp_path):
    engine = create_database_engine(get_settings().test_database_url)
    async with async_sessionmaker(engine, expire_on_commit=False, autoflush=False)() as session:
        try:
            service = KnowledgeOperations(session, embedding_service=Embeddings(),
                storage=LocalDocumentStorage(tmp_path/'storage'))
            yield session, service
        finally:
            await session.rollback()
            service.cleanup()
    await engine.dispose()


@pytest.mark.asyncio
async def test_pipeline_duplicate_versions_history_and_reindex(db, tmp_path):
    session, service = db
    path = tmp_path/(str(uuid4())+'.md')
    path.write_text('# Approved portal guide\n\nUse the projects screen to find the project owner.')
    first = await service.ingest(path)
    assert first['chunks_created'] > 0 and first['indexed_chunks'] > 0
    from uuid import UUID
    doc_id, version_id = UUID(first['document_id']), UUID(first['version_id'])
    duplicate = await service.ingest(path)
    assert duplicate['duplicate'] and duplicate['indexed_chunks'] == 0
    assert duplicate['version_id'] == first['version_id']
    assert (await service.reindex(doc_id, version_id))['indexed_chunks'] == 0
    original = path.read_text()
    path.write_text('# Approved portal guide\n\nUse the project details screen to find the owner.')
    second = await service.ingest(path, document_id=doc_id)
    assert second['version_number'] == 2 and second['indexed_chunks'] > 0
    history = await service.history(doc_id)
    assert [v['version_number'] for v in history['versions']] == [2, 1]
    assert [v['active'] for v in history['versions']] == [True, False]
    assert len(history['ingestion_jobs']) == 3
    assert all(v['index_status'] == 'indexed' for v in history['versions'])
    metadata = await service.document(doc_id)
    assert metadata['active_version']['version_number'] == 2
    assert 'storage' not in str(metadata) and str(tmp_path) not in str(history)
    assert 'content' not in metadata and 'error_message' not in str(history)
    # Legacy duplicate behavior for historic content is deliberately preserved.
    path.write_text(original)
    historic = await service.ingest(path)
    assert historic['duplicate'] and not historic['active']
    assert (await service.document(doc_id))['active_version']['version_number'] == 2
    with pytest.raises(OperationsError, match='INACTIVE_VERSION'):
        await service.reindex(doc_id, version_id)


@pytest.mark.asyncio
async def test_version_indexing_does_not_consume_other_pending_chunks(db, tmp_path):
    session, service = db
    a, b = tmp_path/(str(uuid4())+'.txt'), tmp_path/(str(uuid4())+'.txt')
    a.write_text('Unindexed original knowledge for WebPortal project login.')
    pending = await service.ingestion.ingest(a)
    b.write_text('New approved WebPortal knowledge for project ownership.')
    result = await service.ingest(b)
    assert result['indexed_chunks'] > 0
    assert await session.scalar(select(func.count(ChunkEmbedding.id)).join(
        KnowledgeChunk, KnowledgeChunk.id == ChunkEmbedding.chunk_id).where(
        KnowledgeChunk.document_version_id == pending.version_id)) == 0


@pytest.mark.asyncio
async def test_index_failure_rollback_and_storage_compensation(db, tmp_path):
    session, service = db
    path = tmp_path/(str(uuid4())+'.md')
    path.write_text('# Private data\n\nA valid document for embedding failure.')
    def broken(texts):
        raise ValueError('sensitive-exception')
    service.indexer.embedding_service.embed_documents = broken
    with pytest.raises(ValueError):
        await service.ingest(path)
    stored = list(service.new_storage)
    assert stored
    await session.rollback()
    service.cleanup()
    assert not any(Path(p).exists() for p in stored)
    assert await session.scalar(select(KnowledgeDocument.id).where(
        KnowledgeDocument.original_filename == path.name)) is None


@pytest.mark.asyncio
async def test_update_target_and_missing_metadata(db, tmp_path):
    _, service = db
    path = tmp_path/'valid.md'
    path.write_text('Valid approved project guide.')
    with pytest.raises(OperationsError, match='DOCUMENT_NOT_FOUND'):
        await service.ingest(path, document_id=uuid4())
    with pytest.raises(OperationsError, match='DOCUMENT_NOT_FOUND'):
        await service.document(uuid4())


@pytest.mark.asyncio
async def test_feedback_database_contract(db):
    session, _ = db
    conversation = Conversation()
    session.add(conversation)
    await session.flush()
    message = Message(conversation_id=conversation.id, role='assistant', content='private answer')
    user = Message(conversation_id=conversation.id, role='user', content='private prompt')
    session.add_all([message, user])
    await session.flush()
    payload = dict(conversation_id=conversation.id, message_id=message.id, is_positive=True)
    assert await record_feedback(session, **payload) == {'status': 'recorded'}
    await record_feedback(session, **payload)
    rows = (await session.scalars(select(Feedback).where(Feedback.message_id == message.id))).all()
    assert len(rows) == 1 and rows[0].comment is None and rows[0].is_positive is True
    with pytest.raises(OperationsError, match='FEEDBACK_ALREADY_RECORDED'):
        await record_feedback(session, **{**payload, 'is_positive': False})
    for invalid in [{'message_id': uuid4()}, {'conversation_id': uuid4()}, {'message_id': user.id}]:
        with pytest.raises(OperationsError, match='MESSAGE_NOT_FOUND'):
            await record_feedback(session, **{**payload, **invalid})

@pytest.mark.asyncio
async def test_batch_success_uses_full_pipeline(db, tmp_path):
    from scripts.ingest_directory import process_files
    session, service = db
    paths = []
    for i in range(2):
        path = tmp_path/(str(uuid4())+'.md')
        path.write_text('# WebPortal\n\nApproved knowledge for project entry and ownership.')
        paths.append(path)
    assert await process_files(paths, processor=service.ingest) == 0
    assert await session.scalar(select(func.count(KnowledgeDocument.id)).where(
        KnowledgeDocument.original_filename.in_([p.name for p in paths]))) == 2
    for path in paths:
        document = (await session.scalars(select(KnowledgeDocument).where(
            KnowledgeDocument.original_filename == path.name))).one()
        metadata = await service.document(document.id)
        assert metadata['active_version']['index_status'] == 'indexed'


@pytest.mark.asyncio
async def test_concurrent_management_writer_is_busy(db):
    session, service = db
    await service.lock()
    engine = create_database_engine(get_settings().test_database_url)
    try:
        async with async_sessionmaker(engine)() as other:
            second = KnowledgeOperations(other, embedding_service=Embeddings())
            with pytest.raises(OperationsError, match='KNOWLEDGE_BUSY'):
                await second.lock()
            await other.rollback()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_safe_display_and_missing_reindex_target(db):
    _, service = db
    assert service._display_name('C:/private/server/file.md') == '[restricted filename]'
    with pytest.raises(OperationsError, match='VERSION_NOT_FOUND'):
        await service.reindex(uuid4(), uuid4())
