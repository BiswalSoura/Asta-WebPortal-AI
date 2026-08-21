from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import (
    DocumentVersion,
    IngestionJob,
    KnowledgeChunk,
    KnowledgeDocument,
)
from app.knowledge.models import DocumentChunk


class KnowledgeRepository:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    async def create_ingestion_job(
        self,
    ) -> IngestionJob:
        job = IngestionJob(
            status="processing",
        )

        self.session.add(job)

        await self.session.flush()

        return job

    async def find_document_by_filename(
        self,
        filename: str,
    ) -> KnowledgeDocument | None:
        result = await self.session.execute(
            select(KnowledgeDocument).where(
                KnowledgeDocument.original_filename
                == filename
            )
        )

        return result.scalar_one_or_none()

    async def find_version_by_hash(
        self,
        document_id: UUID,
        content_hash: str,
    ) -> DocumentVersion | None:
        result = await self.session.execute(
            select(DocumentVersion).where(
                DocumentVersion.document_id
                == document_id,
                DocumentVersion.content_hash
                == content_hash,
            )
        )

        return result.scalar_one_or_none()

    async def next_version_number(
        self,
        document_id: UUID,
    ) -> int:
        result = await self.session.execute(
            select(
                func.coalesce(
                    func.max(
                        DocumentVersion.version_number
                    ),
                    0,
                )
            ).where(
                DocumentVersion.document_id
                == document_id
            )
        )

        current_maximum = result.scalar_one()

        return int(current_maximum) + 1

    async def deactivate_versions(
        self,
        document_id: UUID,
    ) -> None:
        await self.session.execute(
            update(DocumentVersion)
            .where(
                DocumentVersion.document_id
                == document_id
            )
            .values(
                is_active=False,
            )
        )

    async def create_document(
        self,
        *,
        name: str,
        original_filename: str,
        source_type: str,
        file_size_bytes: int,
    ) -> KnowledgeDocument:
        document = KnowledgeDocument(
            name=name,
            original_filename=original_filename,
            source_type=source_type,
            file_size_bytes=file_size_bytes,
            status="processing",
        )

        self.session.add(document)

        await self.session.flush()

        return document

    async def create_version(
        self,
        *,
        document_id: UUID,
        version_number: int,
        content_hash: str,
        storage_path: str,
    ) -> DocumentVersion:
        version = DocumentVersion(
            document_id=document_id,
            version_number=version_number,
            content_hash=content_hash,
            storage_path=storage_path,
            is_active=True,
        )

        self.session.add(version)

        await self.session.flush()

        return version

    async def create_chunks(
        self,
        *,
        document_version_id: UUID,
        chunks: list[DocumentChunk],
    ) -> list[KnowledgeChunk]:
        records = [
            KnowledgeChunk(
                document_version_id=document_version_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                section_title=chunk.section_title,
                page_number=chunk.page_number,
                token_count=chunk.token_count,
                source_metadata=chunk.source_metadata,
            )
            for chunk in chunks
        ]

        self.session.add_all(records)

        await self.session.flush()

        return records