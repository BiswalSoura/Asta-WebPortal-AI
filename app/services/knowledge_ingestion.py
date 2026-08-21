from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.database.repositories import (
    KnowledgeRepository,
)
from app.knowledge.chunking import SectionChunker
from app.knowledge.models import IngestionResult
from app.knowledge.processors import DocumentProcessor
from app.services.document_storage import (
    LocalDocumentStorage,
)


class KnowledgeIngestionService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        processor: DocumentProcessor | None = None,
        chunker: SectionChunker | None = None,
        storage: LocalDocumentStorage | None = None,
    ) -> None:
        settings = get_settings()

        self.repository = KnowledgeRepository(
            session
        )

        self.processor = (
            processor
            or DocumentProcessor()
        )

        self.chunker = (
            chunker
            or SectionChunker()
        )

        self.storage = (
            storage
            or LocalDocumentStorage(
                settings.document_storage_path
            )
        )

    async def ingest(
        self,
        file_path: str | Path,
    ) -> IngestionResult:
        job = (
            await self.repository
            .create_ingestion_job()
        )

        stored_path: str | None = None

        try:
            parsed_document = (
                self.processor.process(
                    file_path
                )
            )

            document = (
                await self.repository
                .find_document_by_filename(
                    parsed_document.source_path.name
                )
            )

            if document is None:
                document = (
                    await self.repository
                    .create_document(
                        name=parsed_document.name,
                        original_filename=(
                            parsed_document
                            .source_path
                            .name
                        ),
                        source_type=(
                            parsed_document.source_type
                        ),
                        file_size_bytes=(
                            parsed_document
                            .file_size_bytes
                        ),
                    )
                )

            else:
                document.status = "processing"
                document.source_type = (
                    parsed_document.source_type
                )
                document.file_size_bytes = (
                    parsed_document.file_size_bytes
                )

            job.document_id = document.id

            existing_version = (
                await self.repository
                .find_version_by_hash(
                    document.id,
                    parsed_document.content_hash,
                )
            )

            if existing_version is not None:
                document.status = "ready"

                job.status = "completed"
                job.completed_at = datetime.now(
                    timezone.utc
                )

                return IngestionResult(
                    document_id=document.id,
                    version_id=existing_version.id,
                    version_number=(
                        existing_version.version_number
                    ),
                    chunks_created=0,
                    duplicate=True,
                )

            version_number = (
                await self.repository
                .next_version_number(
                    document.id
                )
            )

            stored_path = self.storage.store(
                parsed_document.source_path,
                document.id,
                version_number,
            )

            await self.repository.deactivate_versions(
                document.id
            )

            version = (
                await self.repository
                .create_version(
                    document_id=document.id,
                    version_number=version_number,
                    content_hash=(
                        parsed_document.content_hash
                    ),
                    storage_path=stored_path,
                )
            )

            chunks = self.chunker.chunk(
                parsed_document
            )

            await self.repository.create_chunks(
                document_version_id=version.id,
                chunks=chunks,
            )

            document.status = "ready"

            job.status = "completed"
            job.completed_at = datetime.now(
                timezone.utc
            )

            return IngestionResult(
                document_id=document.id,
                version_id=version.id,
                version_number=version_number,
                chunks_created=len(chunks),
                duplicate=False,
            )

        except Exception as exc:
            job.status = "failed"
            job.error_message = str(exc)[:2000]
            job.completed_at = datetime.now(
                timezone.utc
            )

            if stored_path is not None:
                self.storage.delete(
                    stored_path
                )

            raise