from app.api.dependencies.services import (
    get_shared_embedding_service,
    get_shared_reranker,
)


def test_ai_model_dependencies_are_singletons() -> None:
    get_shared_embedding_service.cache_clear()
    get_shared_reranker.cache_clear()

    embedding_one = (
        get_shared_embedding_service()
    )

    embedding_two = (
        get_shared_embedding_service()
    )

    reranker_one = (
        get_shared_reranker()
    )

    reranker_two = (
        get_shared_reranker()
    )

    assert embedding_one is embedding_two

    assert reranker_one is reranker_two