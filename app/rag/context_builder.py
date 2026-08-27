from app.retrieval.models import (
    RetrievalCandidate,
)


class RAGContextBuilder:
    def build(
        self,
        candidates: list[
            RetrievalCandidate
        ],
    ) -> str:
        sections: list[str] = []

        for index, candidate in enumerate(
            candidates,
            start=1,
        ):
            source_lines = [
                f"[SOURCE {index}]",
                (
                    "Document: "
                    f"{candidate.original_filename}"
                ),
            ]

            if candidate.section_title:
                source_lines.append(
                    (
                        "Section: "
                        f"{candidate.section_title}"
                    )
                )

            if candidate.page_number is not None:
                source_lines.append(
                    (
                        "Page: "
                        f"{candidate.page_number}"
                    )
                )

            source_lines.extend(
                [
                    "Content:",
                    candidate.content,
                ]
            )

            sections.append(
                "\n".join(source_lines)
            )

        return "\n\n".join(sections)