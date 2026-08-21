from pathlib import Path

import pymupdf

from app.knowledge.loaders.base import DocumentLoader
from app.knowledge.models import ParsedSection


class PdfDocumentLoader(DocumentLoader):
    def load(
        self,
        path: Path,
    ) -> list[ParsedSection]:
        sections: list[ParsedSection] = []

        with pymupdf.open(path) as document:
            for page_index, page in enumerate(
                document,
                start=1,
            ):
                content = page.get_text(
                    "text"
                ).strip()

                if not content:
                    continue

                sections.append(
                    ParsedSection(
                        title=None,
                        content=content,
                        page_number=page_index,
                        metadata={
                            "pdf_page": page_index,
                        },
                    )
                )

        return sections