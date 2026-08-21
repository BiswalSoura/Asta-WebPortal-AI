from pathlib import Path

from app.knowledge.loaders.base import DocumentLoader
from app.knowledge.models import ParsedSection


class TextDocumentLoader(DocumentLoader):
    def load(
        self,
        path: Path,
    ) -> list[ParsedSection]:
        content = path.read_text(
            encoding="utf-8-sig",
        )

        return [
            ParsedSection(
                title=None,
                content=content,
            )
        ]