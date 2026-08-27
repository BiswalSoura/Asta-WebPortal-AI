from uuid import uuid4

from app.rag.context_builder import (
    RAGContextBuilder,
)
from app.retrieval.models import (
    RetrievalCandidate,
)


def test_context_builder_includes_source_metadata() -> None:
    candidate = RetrievalCandidate(
        chunk_id=uuid4(),
        document_id=uuid4(),
        document_name="WebPortal Guide",
        original_filename=(
            "webportal-guide.md"
        ),
        content=(
            "Use the Create New Project page."
        ),
        section_title=(
            "Create New Project"
        ),
        page_number=None,
        source_metadata={},
        vector_score=0.9,
        rerank_score=0.95,
    )

    builder = RAGContextBuilder()

    result = builder.build(
        [candidate]
    )

    assert "[SOURCE 1]" in result

    assert (
        "webportal-guide.md"
        in result
    )

    assert (
        "Create New Project"
        in result
    )