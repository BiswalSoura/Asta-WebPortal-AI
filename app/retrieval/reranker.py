import torch
from dataclasses import replace
from typing import Any, Protocol

from app.retrieval.exceptions import (
    RerankingError,
)
from app.retrieval.models import (
    RetrievalCandidate,
)


class CrossEncoderProtocol(Protocol):
    def predict(
        self,
        sentences: list[
            tuple[str, str]
        ],
        **kwargs: Any,
    ) -> Any:
        ...


class CrossEncoderReranker:
    def __init__(
        self,
        *,
        model_name: str,
        device: str,
        encoder: CrossEncoderProtocol
        | None = None,
    ) -> None:
        self.model_name = model_name
        self.device = device
        self._encoder = encoder

    def rerank(
    self,
    query: str,
    candidates: list[
        RetrievalCandidate
    ],
    *,
    top_k: int,
    min_score: float | None = None,
) -> list[RetrievalCandidate]:
        if not candidates:
            return []

        if top_k <= 0:
            raise ValueError(
                "top_k must be greater than zero."
            )

        encoder = self._get_encoder()

        pairs = [
            (
                query,
                candidate.content,
            )
            for candidate in candidates
        ]

        try:
            raw_scores = encoder.predict(
                pairs,
                show_progress_bar=False,
            )

        except Exception as exc:
            raise RerankingError(
                "Failed to rerank retrieval candidates."
            ) from exc

        scores = (
            raw_scores.tolist()
            if hasattr(
                raw_scores,
                "tolist",
            )
            else list(raw_scores)
        )

        if len(scores) != len(candidates):
            raise RerankingError(
                (
                    "Reranker returned an unexpected "
                    "number of scores."
                )
            )

        reranked = [
            replace(
                candidate,
                rerank_score=float(score),
            )
            for candidate, score in zip(
                candidates,
                scores,
                strict=True,
            )
        ]

        reranked.sort(
            key=lambda candidate: (
                candidate.rerank_score
                if candidate.rerank_score
                is not None
                else float("-inf")
            ),
            reverse=True,       
        )
        if min_score is not None:
            reranked = [
            candidate
            for candidate in reranked
            if (
                candidate.rerank_score
                is not None
                and candidate.rerank_score
                >= min_score
            )
        ]

        return reranked[:top_k]

    def _get_encoder(
        self,
    ) -> CrossEncoderProtocol:
        if self._encoder is None:
            from sentence_transformers import (
                CrossEncoder,
            )

            self._encoder = CrossEncoder(
                self.model_name,
                device=self.device,
                activation_fn=torch.nn.Sigmoid(),
            )

        return self._encoder