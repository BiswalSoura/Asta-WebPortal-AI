from pathlib import Path

import pytest

from app.knowledge.exceptions import (
    EmptyDocumentError,
    UnsupportedDocumentTypeError,
)
from app.knowledge.processors import (
    DocumentProcessor,
)


def test_processor_creates_document_metadata(
    tmp_path: Path,
) -> None:
    path = tmp_path / "webportal.txt"

    path.write_text(
        "Create New Project help.",
        encoding="utf-8",
    )

    processor = DocumentProcessor()

    result = processor.process(path)

    assert result.name == "webportal"
    assert result.source_type == "txt"
    assert len(result.content_hash) == 64
    assert len(result.sections) == 1


def test_processor_rejects_unsupported_file(
    tmp_path: Path,
) -> None:
    path = tmp_path / "sample.exe"

    path.write_bytes(b"not a document")

    processor = DocumentProcessor()

    with pytest.raises(
        UnsupportedDocumentTypeError
    ):
        processor.process(path)


def test_processor_rejects_empty_document(
    tmp_path: Path,
) -> None:
    path = tmp_path / "empty.txt"

    path.write_text(
        "",
        encoding="utf-8",
    )

    processor = DocumentProcessor()

    with pytest.raises(
        EmptyDocumentError
    ):
        processor.process(path)