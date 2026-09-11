"""M16 orchestration. Existing ingestion, chunking and embeddings remain authoritative."""
from pathlib import Path
import re

from sqlalchemy import func, select, text

from app.database.models import (ChunkEmbedding, DocumentVersion, IngestionJob,
                                 KnowledgeChunk, KnowledgeDocument)
from app.knowledge.constants import SUPPORTED_DOCUMENT_EXTENSIONS
from app.services.knowledge_ingestion import KnowledgeIngestionService
from app.services.embedding_indexing import EmbeddingIndexingService


class OperationsError(Exception):
    def __init__(self, code="PROCESSING_FAILED", status=422):
        self.code, self.status = code, status
        super().__init__(code)


def safe_filename(value):
    # Reject rather than silently collide different client paths/names. Portable on Windows/Linux.
    if (not isinstance(value, str) or not 1 <= len(value) <= 180
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 ._-]*", value)
            or value.endswith((".", " ")) or ".." in value
            or value.split('.')[0].rstrip(' .').upper() in {
                'CON', 'PRN', 'AUX', 'NUL',
                *(f'COM{i}' for i in range(1, 10)), *(f'LPT{i}' for i in range(1, 10))}):
        raise OperationsError("INVALID_FILENAME", 422)
    if Path(value).suffix.lower() not in SUPPORTED_DOCUMENT_EXTENSIONS:
        raise OperationsError("UNSUPPORTED_DOCUMENT_TYPE", 415)
    return value


class KnowledgeOperations:
    """Caller owns commit/rollback. All M16 writers serialize on a DB transaction lock.

    Legacy scripts must not run concurrently with M16 writers. Storage written before
    embedding failure is compensated by the API/CLI after rollback via cleanup().
    """
    def __init__(self, session, *, embedding_service=None, storage=None):
        self.session = session
        self.ingestion = KnowledgeIngestionService(session, storage=storage)
        self.indexer = EmbeddingIndexingService(session, embedding_service=embedding_service)
        self.new_storage = []

    async def lock(self):
        # Non-blocking across processes, not an in-memory production rate limiter.
        acquired = await self.session.scalar(text("SELECT pg_try_advisory_xact_lock(16160016)"))
        if not acquired:
            raise OperationsError("KNOWLEDGE_BUSY", 409)

    def cleanup(self):
        for path in self.new_storage:
            self.ingestion.storage.delete(path)
        self.new_storage.clear()

    async def ingest(self, path, *, document_id=None):
        safe_filename(Path(path).name)
        await self.lock()
        if document_id is not None:
            document = await self.session.get(KnowledgeDocument, document_id)
            if document is None:
                raise OperationsError("DOCUMENT_NOT_FOUND", 404)
            if document.original_filename != Path(path).name:
                raise OperationsError("FILENAME_MISMATCH", 409)
        result = await self.ingestion.ingest(path)
        version = await self.session.get(DocumentVersion, result.version_id)
        if not result.duplicate and version.storage_path:
            self.new_storage.append(version.storage_path)
        # Re-uploading historical bytes is an existing duplicate, NOT a rollback to old content.
        indexed = await self.index_version(version) if version.is_active else 0
        await self.session.flush()
        return {"document_id": str(result.document_id), "version_id": str(result.version_id),
                "version_number": result.version_number, "duplicate": result.duplicate,
                "active": version.is_active, "chunks_created": result.chunks_created,
                "indexed_chunks": indexed}

    async def index_version(self, version):
        total = 0
        while True:
            result = await self.indexer.index_batch(version_id=version.id)
            if not result.indexed_chunks:
                return total
            total += result.indexed_chunks

    async def reindex(self, document_id, version_id):
        await self.lock()
        version = await self.session.get(DocumentVersion, version_id)
        if version is None or version.document_id != document_id:
            raise OperationsError("VERSION_NOT_FOUND", 404)
        if not version.is_active:
            raise OperationsError("INACTIVE_VERSION", 409)
        return {"version_id": str(version.id), "indexed_chunks": await self.index_version(version)}

    async def document(self, document_id):
        doc = await self.session.get(KnowledgeDocument, document_id)
        if doc is None:
            raise OperationsError("DOCUMENT_NOT_FOUND", 404)
        return await self._metadata(doc)

    async def documents(self, limit=50, offset=0):
        docs = (await self.session.scalars(select(KnowledgeDocument)
                .order_by(KnowledgeDocument.created_at, KnowledgeDocument.id)
                .limit(limit).offset(offset))).all()
        return [await self._metadata(doc) for doc in docs]

    async def _metadata(self, doc):
        active = (await self.session.scalars(select(DocumentVersion).where(
            DocumentVersion.document_id == doc.id, DocumentVersion.is_active.is_(True))
            .order_by(DocumentVersion.version_number.desc()).limit(1))).first()
        return {"document_id": str(doc.id), "filename": self._display_name(doc.original_filename),
                "source_type": doc.source_type if doc.source_type in {'md','txt','pdf','docx'} else 'unknown',
                "status": doc.status if doc.status in {'pending','processing','ready','failed'} else 'unknown',
                "file_size_bytes": doc.file_size_bytes, "created_at": doc.created_at,
                "updated_at": doc.updated_at,
                "active_version": await self._version_metadata(active) if active else None}

    @staticmethod
    def _display_name(value):
        # Existing legacy records may have unsafe display names; never return a stored path.
        try:
            return safe_filename(value)
        except OperationsError:
            return "[restricted filename]"

    async def _version_metadata(self, version):
        chunks, embedded = (await self.session.execute(select(
            func.count(KnowledgeChunk.id), func.count(ChunkEmbedding.id))
            .select_from(KnowledgeChunk).outerjoin(ChunkEmbedding,
                ChunkEmbedding.chunk_id == KnowledgeChunk.id)
            .where(KnowledgeChunk.document_version_id == version.id))).one()
        return {"version_id": str(version.id), "version_number": version.version_number,
                "active": version.is_active, "sha256": version.content_hash,
                "created_at": version.created_at, "processed_at": version.processed_at,
                "chunk_count": chunks, "embedding_count": embedded,
                "index_status": "indexed" if chunks > 0 and chunks == embedded else "incomplete"}

    async def history(self, document_id, limit=50, offset=0):
        if await self.session.get(KnowledgeDocument, document_id) is None:
            raise OperationsError("DOCUMENT_NOT_FOUND", 404)
        versions = (await self.session.scalars(select(DocumentVersion)
            .where(DocumentVersion.document_id == document_id)
            .order_by(DocumentVersion.version_number.desc()).limit(limit).offset(offset))).all()
        jobs = (await self.session.scalars(select(IngestionJob)
            .where(IngestionJob.document_id == document_id)
            .order_by(IngestionJob.created_at.desc(), IngestionJob.id)
            .limit(limit).offset(offset))).all()
        return {"versions": [await self._version_metadata(v) for v in versions],
                "ingestion_jobs": [{"job_id": str(j.id),
                    "status": j.status if j.status in {'queued','processing','completed','failed'} else 'unknown',
                    "created_at": j.created_at, "started_at": j.started_at,
                    "completed_at": j.completed_at} for j in jobs]}
