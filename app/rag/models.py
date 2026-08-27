from dataclasses import dataclass


@dataclass(frozen=True)
class RAGSource:
    document_name: str
    original_filename: str
    section_title: str | None
    page_number: int | None
    vector_score: float
    rerank_score: float | None


@dataclass(frozen=True)
class RAGAnswer:
    answer: str

    sources: tuple[RAGSource, ...]

    model: str | None

    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None

    grounded: bool