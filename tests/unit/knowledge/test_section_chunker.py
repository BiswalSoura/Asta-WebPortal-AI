from pathlib import Path

from app.knowledge.chunking import (
    SectionChunker,
)
from app.knowledge.models import (
    ParsedDocument,
    ParsedSection,
)


def _document(
    content: str,
) -> ParsedDocument:
    return ParsedDocument(
        source_path=Path(
            "webportal.txt"
        ),
        name="webportal",
        source_type="txt",
        content_hash="a" * 64,
        file_size_bytes=len(content),
        sections=(
            ParsedSection(
                title="Test Section",
                content=content,
            ),
        ),
    )


def test_short_section_creates_one_chunk() -> None:
    chunker = SectionChunker(
        chunk_size=100,
        overlap=10,
    )

    chunks = chunker.chunk(
        _document(
            "Short WebPortal content."
        )
    )

    assert len(chunks) == 1
    assert chunks[0].chunk_index == 0


def test_long_section_creates_multiple_chunks() -> None:
    content = (
        "WebPortal project information. "
        * 50
    )

    chunker = SectionChunker(
        chunk_size=200,
        overlap=20,
    )

    chunks = chunker.chunk(
        _document(content)
    )

    assert len(chunks) > 1


def test_chunk_preserves_section_metadata() -> None:
    chunker = SectionChunker()

    chunks = chunker.chunk(
        _document(
            "Project List explanation."
        )
    )

    assert (
        chunks[0].section_title
        == "Test Section"
    )

    assert (
        chunks[0].source_metadata[
            "source_filename"
        ]
        == "webportal.txt"
    )