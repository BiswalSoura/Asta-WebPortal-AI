from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class IngestionResult:
    document_id: UUID
    version_id: UUID
    version_number: int
    chunks_created: int
    duplicate: bool