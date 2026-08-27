from uuid import uuid4

from app.retrieval.models import (
    RetrievalCandidate,
)
from app.retrieval.reranker import (
    CrossEncoderReranker,
)


class FakeCrossEncoder:
    def predict(
        self,
        sentences,
        **kwargs,
    ):
        del sentences, kwargs

        return [
            0.1,
            0.9,
        ]


def _candidate(
    content: str,
    vector_score: float,
) -> RetrievalCandidate:
    return RetrievalCandidate(
        chunk_id=uuid4(),
        document_id=uuid4(),
        document_name="WebPortal Guide",
        original_filename=(
            "webportal-guide.md"
        ),
        content=content,
        section_title=None,
        page_number=None,
        source_metadata={},
        vector_score=vector_score,
    )


def test_reranker_orders_by_cross_encoder_score() -> None:
    reranker = CrossEncoderReranker(
        model_name="fake-model",
        device="cpu",
        encoder=FakeCrossEncoder(),
    )

    results = reranker.rerank(
        "How do I create a project?",
        [
            _candidate(
                "Project List help.",
                0.95,
            ),
            _candidate(
                "Create New Project help.",
                0.80,
            ),
        ],
        top_k=2,
    )

    assert (
        results[0].content
        == "Create New Project help."
    )

    assert results[0].rerank_score == 0.9


def test_reranker_respects_top_k() -> None:
    reranker = CrossEncoderReranker(
        model_name="fake-model",
        device="cpu",
        encoder=FakeCrossEncoder(),
    )

    results = reranker.rerank(
        "test",
        [
            _candidate("first", 0.8),
            _candidate("second", 0.7),
        ],
        top_k=1,
    )

    assert len(results) == 1

def test_reranker_filters_low_relevance_scores() -> None:
    reranker = CrossEncoderReranker(
        model_name="fake-model",
        device="cpu",
        encoder=FakeCrossEncoder(),
    )

    results = reranker.rerank(
        "test",
        [
            _candidate("low relevance", 0.8),
            _candidate("high relevance", 0.7),
        ],
        top_k=2,
        min_score=0.5,
    )

    assert len(results) == 1

    assert (
        results[0].content
        == "high relevance"
    )