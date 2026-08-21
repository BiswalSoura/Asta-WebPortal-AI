import math

from app.knowledge.constants import (
    DEFAULT_CHUNK_OVERLAP_CHARS,
    DEFAULT_CHUNK_SIZE_CHARS,
)
from app.knowledge.models import (
    DocumentChunk,
    ParsedDocument,
)


class SectionChunker:
    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE_CHARS,
        overlap: int = DEFAULT_CHUNK_OVERLAP_CHARS,
    ) -> None:
        if chunk_size <= 0:
            raise ValueError(
                "chunk_size must be greater than zero."
            )

        if overlap < 0:
            raise ValueError(
                "overlap cannot be negative."
            )

        if overlap >= chunk_size:
            raise ValueError(
                "overlap must be smaller than chunk_size."
            )

        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(
        self,
        document: ParsedDocument,
    ) -> list[DocumentChunk]:
        chunks: list[DocumentChunk] = []

        chunk_index = 0

        for section in document.sections:
            for content in self._split_text(
                section.content
            ):
                metadata = {
                    "source_filename": (
                        document.source_path.name
                    ),
                    "source_type": (
                        document.source_type
                    ),
                    "content_hash": (
                        document.content_hash
                    ),
                    **section.metadata,
                }

                chunks.append(
                    DocumentChunk(
                        chunk_index=chunk_index,
                        content=content,
                        section_title=section.title,
                        page_number=section.page_number,
                        token_count=self._estimate_tokens(
                            content
                        ),
                        source_metadata=metadata,
                    )
                )

                chunk_index += 1

        return chunks

    def _split_text(
        self,
        text: str,
    ) -> list[str]:
        text = text.strip()

        if len(text) <= self.chunk_size:
            return [text]

        chunks: list[str] = []

        start = 0
        text_length = len(text)

        while start < text_length:
            maximum_end = min(
                start + self.chunk_size,
                text_length,
            )

            end = self._find_breakpoint(
                text,
                start,
                maximum_end,
            )

            chunk = text[start:end].strip()

            if chunk:
                chunks.append(chunk)

            if end >= text_length:
                break

            next_start = max(
                end - self.overlap,
                start + 1,
            )

            start = next_start

        return chunks

    def _find_breakpoint(
        self,
        text: str,
        start: int,
        maximum_end: int,
    ) -> int:
        if maximum_end >= len(text):
            return len(text)

        minimum_break = start + int(
            self.chunk_size * 0.6
        )

        boundaries = (
            "\n\n",
            ". ",
            "\n",
            " ",
        )

        for boundary in boundaries:
            position = text.rfind(
                boundary,
                minimum_break,
                maximum_end,
            )

            if position != -1:
                return position + len(boundary)

        return maximum_end

    @staticmethod
    def _estimate_tokens(
        text: str,
    ) -> int:
        return max(
            1,
            math.ceil(len(text) / 4),
        )