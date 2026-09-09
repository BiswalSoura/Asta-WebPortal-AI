"""Topic-level metrics over the final reranked, thresholded results."""

import re
import unicodedata
from dataclasses import dataclass


def normalize(value: str) -> str:
    # Token boundaries prevent 'apn' matching 'apnea'; punctuation/spacing are immaterial.
    return " ".join(re.findall(r"\w+", unicodedata.normalize("NFKC", value).casefold()))


def contains(text: str, term: str) -> bool:
    return f" {normalize(term)} " in f" {normalize(text)} "


def section_rank(sections: list[str | None], expected: str) -> int | None:
    return next((rank for rank, section in enumerate(sections, 1)
                 if section and normalize(section) == normalize(expected)), None)


@dataclass(frozen=True)
class RetrievalMetrics:
    expected_section_rank: int | None
    top1_correct: bool
    recall_at_k: float
    reciprocal_rank: float


def retrieval_metrics(sections: list[str | None], expected: str, k: int) -> RetrievalMetrics:
    if k < 1:
        raise ValueError("K must be positive")
    rank = section_rank(sections, expected)
    return RetrievalMetrics(rank, rank == 1, float(rank is not None and rank <= k),
                            1.0 / rank if rank else 0.0)


def aggregate_retrieval(items: list[RetrievalMetrics]) -> dict[str, float | int]:
    count = len(items)
    return {
        "cases": count,
        "top1_accuracy": sum(item.top1_correct for item in items) / count if count else 0.0,
        "recall_at_k": sum(item.recall_at_k for item in items) / count if count else 0.0,
        "mrr": sum(item.reciprocal_rank for item in items) / count if count else 0.0,
    }
