"""Explicit report DTOs: deliberately exclude answers, prompts, settings and exceptions."""

from typing import Literal

from pydantic import Field

from app.evaluation.cases import Category, StrictModel


class RankedResult(StrictModel):
    rank: int
    chunk_id: str
    section: str | None
    vector_score: float
    rerank_score: float | None


class Observation(StrictModel):
    elapsed_seconds: float = 0.0
    model: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    grounded: bool | None = None
    source_sections: list[str | None] = Field(default_factory=list)
    contextualized: bool | None = None
    retrieval_calls: int = 0
    rag_calls: int = 0
    llm_calls: int = 0


class CaseResult(StrictModel):
    id: str
    category: Category
    query: str | None = None
    expected_section: str | None = None
    expected_topic: str | None = None
    checks: dict[str, bool] = Field(default_factory=dict)
    error_code: Literal["connection_error", "timeout", "provider_error", "service_error"] | None = None
    observation: Observation = Field(default_factory=Observation)
    ranked_results: list[RankedResult] = Field(default_factory=list)
    k: int | None = None
    expected_section_rank: int | None = None
    top1_correct: bool = False
    recall_at_k: float = 0.0
    reciprocal_rank: float = 0.0
    steps: list["CaseResult"] = Field(default_factory=list)

    @property
    def passed(self) -> bool:
        return (self.error_code is None and bool(self.checks) and all(self.checks.values())
                and all(s.passed for s in self.steps))


class RegressionResult(StrictModel):
    name: Literal["python", "node"]
    passed: bool
    tests: int = 0
    failures: int = 0
    errors: int = 0
    skipped: int = 0


class PipelineSummary(StrictModel):
    embedding_model: str
    embedding_device: str
    reranker_model: str
    reranker_device: str
    retrieval_top_k: int
    retrieval_final_k: int
    reranker_min_score: float
    groq_model: str
    llm_temperature: float


class Report(StrictModel):
    schema_version: Literal[1] = 1
    run_id: str
    started_at: str
    suite_name: str
    suite_sha256: str
    baseline_commit: str | None = None
    settings_summary: PipelineSummary | None = None
    corpus_sha256: str | None = None
    corpus_sections: dict[str, int] = Field(default_factory=dict)
    regressions: list[RegressionResult] = Field(default_factory=list)
    results: list[CaseResult] = Field(default_factory=list)
    retrieval_metrics: dict[str, float | int] = Field(default_factory=dict)
    category_summary: dict[str, dict[str, int]] = Field(default_factory=dict)
    gates: dict[str, bool] = Field(default_factory=dict)
    elapsed_seconds: float = 0.0
    status: Literal["PASS", "FAIL"] = "FAIL"
    error_code: Literal["invalid_cases", "runtime_error", "regression_failure"] | None = None
