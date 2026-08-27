from dataclasses import dataclass
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class RetrievalCandidate:
    chunk_id: UUID
    document_id: UUID

    document_name: str
    original_filename: str

    content: str

    section_title: str | None
    page_number: int | None

    source_metadata: dict[str, Any]

    vector_score: float
    rerank_score: float | None = None