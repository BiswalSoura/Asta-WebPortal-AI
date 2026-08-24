from dataclasses import dataclass


@dataclass(frozen=True)
class EmbeddingIndexResult:
    indexed_chunks: int
    model_name: str
    dimensions: int