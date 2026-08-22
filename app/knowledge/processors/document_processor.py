import hashlib
from pathlib import Path

from app.knowledge.constants import (
    MAX_DOCUMENT_SIZE_BYTES,
    SUPPORTED_DOCUMENT_EXTENSIONS,
)
from app.knowledge.exceptions import (
    DocumentNotFoundError,
    DocumentTooLargeError,
    EmptyDocumentError,
    UnsupportedDocumentTypeError,
)
from app.knowledge.loaders import (
    get_document_loader,
)
from app.knowledge.models import (
    ParsedDocument,
    ParsedSection,
)
from app.knowledge.processors.text_normalizer import (
    normalize_text,
)


class DocumentProcessor:
    def process(
        self,
        file_path: str | Path,
    ) -> ParsedDocument:
        path = Path(file_path)

        if not path.exists() or not path.is_file():
            raise DocumentNotFoundError(
                str(path)
            )

        extension = path.suffix.lower()

        if (
            extension
            not in SUPPORTED_DOCUMENT_EXTENSIONS
        ):
            raise UnsupportedDocumentTypeError(
                extension
            )

        file_size = path.stat().st_size

        if file_size > MAX_DOCUMENT_SIZE_BYTES:
            raise DocumentTooLargeError(
                MAX_DOCUMENT_SIZE_BYTES
            )

        loader = get_document_loader(path)

        raw_sections = loader.load(path)

        sections: list[ParsedSection] = []

        for section in raw_sections:
            normalized_content = normalize_text(
                section.content
            )

            if not normalized_content:
                continue

            normalized_title = (
                normalize_text(section.title)
                if section.title
                else None
            )

            sections.append(
                ParsedSection(
                    title=normalized_title,
                    content=normalized_content,
                    page_number=section.page_number,
                    metadata=section.metadata,
                )
            )

        if not sections:
            raise EmptyDocumentError()

        return ParsedDocument(
            source_path=path,
            name=path.stem,
            source_type=extension.removeprefix("."),
            content_hash=self._sha256(path),
            file_size_bytes=file_size,
            sections=tuple(sections),
        )

    @staticmethod
    def _sha256(
        path: Path,
    ) -> str:
        digest = hashlib.sha256()

        with path.open("rb") as file:
            for block in iter(
                lambda: file.read(1024 * 1024),
                b"",
            ):
                digest.update(block)

        return digest.hexdigest()