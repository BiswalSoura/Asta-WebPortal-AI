import re
from pathlib import Path

from app.knowledge.loaders.base import DocumentLoader
from app.knowledge.models import ParsedSection


HEADING_PATTERN = re.compile(
    r"^#{1,6}\s+(.+?)\s*$"
)


class MarkdownDocumentLoader(DocumentLoader):
    def load(
        self,
        path: Path,
    ) -> list[ParsedSection]:
        content = path.read_text(
            encoding="utf-8-sig",
        )

        sections: list[ParsedSection] = []

        current_title: str | None = None
        current_lines: list[str] = []

        def flush_section() -> None:
            nonlocal current_lines

            section_content = "\n".join(
                current_lines
            ).strip()

            if section_content:
                sections.append(
                    ParsedSection(
                        title=current_title,
                        content=section_content,
                    )
                )

            current_lines = []

        for line in content.splitlines():
            match = HEADING_PATTERN.match(line)

            if match:
                flush_section()
                current_title = match.group(1).strip()
                continue

            current_lines.append(line)

        flush_section()

        return sections