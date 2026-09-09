"""Deterministic assertions; no generated prose is copied into results."""

from dataclasses import asdict

from app.evaluation.cases import AnswerCase, RetrievalCase
from app.evaluation.metrics import contains, retrieval_metrics
from app.evaluation.results import CaseResult, Observation, RankedResult
from app.rag.models import RAGAnswer
from app.retrieval.models import RetrievalCandidate


def evaluate_retrieval(case: RetrievalCase, candidates: list[RetrievalCandidate]) -> CaseResult:
    metrics = retrieval_metrics([c.section_title for c in candidates], case.expected_section, case.k)
    rank = metrics.expected_section_rank
    return CaseResult(
        id=case.id, category=case.category, query=case.query,
        expected_section=case.expected_section, expected_topic=case.expected_topic, k=case.k,
        checks={"ranking": rank is not None and rank <= case.max_rank,
                "recall": metrics.recall_at_k == 1.0},
        ranked_results=[RankedResult(rank=i, chunk_id=str(c.chunk_id), section=c.section_title,
                                     vector_score=c.vector_score, rerank_score=c.rerank_score)
                        for i, c in enumerate(candidates, 1)],
        **asdict(metrics),
    )


def evaluate_answer(case: AnswerCase, answer: RAGAnswer, observation: Observation) -> CaseResult:
    sections = [source.section_title for source in answer.sources]
    checks = {
        "grounded": answer.grounded == case.expected_grounded,
        "model_present": bool(answer.model) == case.expected_model,
        "sources_present": bool(answer.sources) == case.expected_sources,
    }
    if case.expected_section:
        from app.evaluation.metrics import section_rank
        checks["source_section"] = section_rank(sections, case.expected_section) is not None
    for i, term in enumerate(case.required_terms):
        checks[f"required_term_{i}"] = contains(answer.answer, term)
    for i, group in enumerate(case.required_any_of):
        checks[f"any_of_{i}"] = any(contains(answer.answer, term) for term in group)
    for i, term in enumerate(case.forbidden_terms):
        checks[f"forbidden_term_{i}"] = not contains(answer.answer, term)
    if case.expected_answer is not None:
        checks["fixed_answer"] = answer.answer == case.expected_answer
    if case.expected_contextualized is not None:
        checks["contextualized"] = observation.contextualized == case.expected_contextualized
    if case.category in {"unsupported", "guardrail"}:
        checks["no_token_usage"] = all(value is None for value in (
            answer.prompt_tokens, answer.completion_tokens, answer.total_tokens))
        checks["no_llm_invocation"] = observation.llm_calls == 0
        if case.category == "guardrail":
            checks["no_rag_invocation"] = observation.rag_calls == 0
            checks["no_retrieval_invocation"] = observation.retrieval_calls == 0
        else:
            checks["real_no_evidence_path"] = (
                observation.rag_calls == 1 and observation.retrieval_calls == 1)
    else:
        checks["real_generation_path"] = (observation.llm_calls == 1
                                           and observation.rag_calls == 1
                                           and observation.retrieval_calls == 1)
    observation.model = answer.model
    observation.prompt_tokens = answer.prompt_tokens
    observation.completion_tokens = answer.completion_tokens
    observation.total_tokens = answer.total_tokens
    observation.grounded = answer.grounded
    observation.source_sections = sections
    return CaseResult(id=case.id, category=case.category, query=case.query,
                      expected_section=case.expected_section, expected_topic=case.expected_topic,
                      checks=checks, observation=observation)
