from collections.abc import Iterator
from pathlib import Path

from docx import Document
from docx.document import Document as DocxDocument
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph

from app.knowledge.loaders.base import DocumentLoader
from app.knowledge.models import ParsedSection


def _iter_document_blocks(
    document: DocxDocument,
) -> Iterator[Paragraph | Table]:
    for child in document.element.body.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(
                child,
                document,
            )

        elif isinstance(child, CT_Tbl):
            yield Table(
                child,
                document,
            )


class DocxDocumentLoader(DocumentLoader):
    def load(
        self,
        path: Path,
    ) -> list[ParsedSection]:
        document = Document(path)

        sections: list[ParsedSection] = []

        current_title: str | None = None
        current_content: list[str] = []

        def flush_section() -> None:
            nonlocal current_content

            content = "\n\n".join(
                current_content
            ).strip()

            if content:
                sections.append(
                    ParsedSection(
                        title=current_title,
                        content=content,
                    )
                )

            current_content = []

        for block in _iter_document_blocks(
            document
        ):
            if isinstance(block, Paragraph):
                text = block.text.strip()

                if not text:
                    continue

                style_name = (
                    block.style.name
                    if block.style is not None
                    else ""
                )

                if style_name.startswith("Heading"):
                    flush_section()
                    current_title = text
                    continue

                current_content.append(text)

            elif isinstance(block, Table):
                table_lines: list[str] = []

                for row in block.rows:
                    cells = [
                        cell.text.strip()
                        for cell in row.cells
                    ]

                    line = " | ".join(cells).strip()

                    if line:
                        table_lines.append(line)

                if table_lines:
                    current_content.append(
                        "\n".join(table_lines)
                    )

        flush_section()

        return sections