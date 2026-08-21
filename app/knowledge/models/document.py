from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ParsedSection:
    title: str | None
    content: str
    page_number: int | None = None
    metadata: dict[str, Any] = field(
        default_factory=dict,
    )


@dataclass(frozen=True)
class ParsedDocument:
    source_path: Path
    name: str
    source_type: str
    content_hash: str
    file_size_bytes: int
    sections: tuple[ParsedSection, ...]