from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DocumentChunk:
    chunk_index: int
    content: str
    section_title: str | None
    page_number: int | None
    token_count: int
    source_metadata: dict[str, Any]