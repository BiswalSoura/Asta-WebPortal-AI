"""Injected orchestration and fail-closed quality gates."""

from collections.abc import Callable
from dataclasses import dataclass
from time import perf_counter
from typing import Any

from app.evaluation.cases import AnswerCase, CaseSuite, ConversationCase, REQUIRED_CATEGORIES
from app.evaluation.evaluators import evaluate_answer, evaluate_retrieval
from app.evaluation.metrics import RetrievalMetrics, aggregate_retrieval
from app.evaluation.results import CaseResult, Observation, Report


class CallCounter:
    """Transparent async delegation; never retains prompts, responses or exceptions."""

    def __init__(self, target: Any, method: str):
        self.target = target
        self.method = method
        self.calls = 0

    def __getattr__(self, name):
        if name != self.method:
            return getattr(self.target, name)

        async def invoke(*args, **kwargs):
            self.calls += 1
            return await getattr(self.target, name)(*args, **kwargs)
        return invoke


@dataclass
class EvaluationServices:
    retrieval: CallCounter
    rag: CallCounter
    llm: CallCounter
    asta: Any
    conversation_scope: Callable

    def counts(self):
        return self.retrieval.calls, self.rag.calls, self.llm.calls

    def observation(self, before, start, contextualized=None):
        retrieval, rag, llm = (now - old for now, old in zip(self.counts(), before, strict=True))
        return Observation(elapsed_seconds=perf_counter() - start, retrieval_calls=retrieval,
                           rag_calls=rag, llm_calls=llm, contextualized=contextualized)


async def run_cases(suite: CaseSuite, services: EvaluationServices,
                    progress: Callable[[CaseResult], None] | None = None) -> list[CaseResult]:
    results = []
    for case in suite.cases:
        before, start = services.counts(), perf_counter()
        steps = []
        try:
            if isinstance(case, ConversationCase):
                async with services.conversation_scope() as (conversation, conversation_id):
                    for step in case.steps:
                        step_before, step_start = services.counts(), perf_counter()
                        reply = await conversation.send_message(
                            conversation_id=conversation_id, message=step.query,
                            request_id=f"m12-{case.id}-{step.id}",
                        )
                        steps.append(evaluate_answer(step, reply.answer, services.observation(
                            step_before, step_start, reply.contextualized)))
                result = CaseResult(id=case.id, category=case.category, steps=steps,
                                    checks={"sequence_complete": len(steps) == len(case.steps),
                                            "cleanup_verified": True},
                                    observation=services.observation(before, start))
            elif isinstance(case, AnswerCase):
                answer = await services.asta.ask(case.query)
                result = evaluate_answer(case, answer, services.observation(before, start))
            else:
                candidates = await services.retrieval.search(case.query)
                result = evaluate_retrieval(case, candidates)
                result.observation = services.observation(before, start)
        except Exception as exc:
            # Even library exceptions can embed credentials or prompt text.
            result = CaseResult(id=case.id, category=case.category,
                                checks={"service_execution": False},
                                steps=steps, error_code=classify_error(exc),
                                observation=services.observation(before, start))
        results.append(result)
        if progress:
            progress(result)
    return results


def classify_error(exc: Exception) -> str:
    """Finite diagnostic codes only; never return exception strings."""
    seen = set()
    while exc is not None and id(exc) not in seen:
        seen.add(id(exc))
        name = type(exc).__name__
        if name in {"APITimeoutError", "TimeoutError", "ReadTimeout", "ConnectTimeout"}:
            return "timeout"
        if name in {"APIConnectionError", "ConnectError", "ConnectionError"}:
            return "connection_error"
        if name in {"APIStatusError", "AuthenticationError", "RateLimitError", "PermissionDeniedError"}:
            return "provider_error"
        exc = exc.__cause__
    return "service_error"


def finalize_report(report: Report, suite: CaseSuite | None) -> Report:
    report.category_summary = {
        category: {
            "total": sum(r.category == category for r in report.results),
            "passed": sum(r.category == category and r.passed for r in report.results),
            "failed": sum(r.category == category and not r.passed for r in report.results),
        } for category in sorted(REQUIRED_CATEGORIES)
    }
    retrieval = [r for r in report.results if r.category == "retrieval"]
    report.retrieval_metrics = aggregate_retrieval([
        RetrievalMetrics(r.expected_section_rank, r.top1_correct, r.recall_at_k, r.reciprocal_rank)
        for r in retrieval
    ])
    expected = [(case.id, case.category) for case in suite.cases] if suite else []
    actual = [(result.id, result.category) for result in report.results]
    report.gates = {
        "complete_suite": bool(expected) and actual == expected,
        "regressions": {r.name for r in report.regressions} == {"python", "node"}
        and len(report.regressions) == 2 and all(
            r.passed and r.tests > 0 and not (r.failures or r.errors or r.skipped)
            for r in report.regressions),
        "execution": report.error_code is None,
        **{category: summary["total"] > 0 and summary["failed"] == 0
           for category, summary in report.category_summary.items()},
    }
    report.status = "PASS" if all(report.gates.values()) else "FAIL"
    return report


def exit_status(report: Report) -> int:
    return 0 if report.status == "PASS" and report.gates and all(report.gates.values()) else 1
