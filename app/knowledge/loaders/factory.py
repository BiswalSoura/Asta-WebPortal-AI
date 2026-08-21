from pathlib import Path

from app.knowledge.exceptions import (
    UnsupportedDocumentTypeError,
)
from app.knowledge.loaders.base import DocumentLoader
from app.knowledge.loaders.docx_loader import (
    DocxDocumentLoader,
)
from app.knowledge.loaders.markdown_loader import (
    MarkdownDocumentLoader,
)
from app.knowledge.loaders.pdf_loader import (
    PdfDocumentLoader,
)
from app.knowledge.loaders.text_loader import (
    TextDocumentLoader,
)


_LOADERS: dict[str, DocumentLoader] = {
    ".docx": DocxDocumentLoader(),
    ".pdf": PdfDocumentLoader(),
    ".txt": TextDocumentLoader(),
    ".md": MarkdownDocumentLoader(),
}


def get_document_loader(
    path: Path,
) -> DocumentLoader:
    extension = path.suffix.lower()

    loader = _LOADERS.get(extension)

    if loader is None:
        raise UnsupportedDocumentTypeError(
            extension
        )

    return loader