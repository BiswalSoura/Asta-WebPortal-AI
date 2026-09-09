from contextlib import asynccontextmanager
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.evaluation.cases import load_cases
from app.evaluation.results import RegressionResult, Report
from app.evaluation.runner import (
    CallCounter, EvaluationServices, classify_error, exit_status, finalize_report, run_cases,
)
from app.llm.models import LLMResponse
from app.rag import RAGService
from app.retrieval.models import RetrievalCandidate
from app.services import AstaService, ConversationService
from tests.evaluation.test_cases import GOLDEN


class MemoryRepository:
    """Controlled repository fake; ConversationService/context builder remain real."""

    def __init__(self):
        self.messages = []

    async def create_conversation(self, **kwargs):
        return SimpleNamespace(id=uuid4())

    async def get_conversation(self, conversation_id):
        return SimpleNamespace(id=conversation_id)

    async def get_recent_messages(self, *, limit, **kwargs):
        return self.messages[-limit:]

    async def add_message(self, *, role, content, **kwargs):
        self.messages.append(SimpleNamespace(role=role, content=content))


def fake_services(suite, *, broken=False):
    answer_cases = [case for case in suite.cases if case.category == "supported_answer"]
    corpus = {
        "Create New Project": (
            "The user enters the Project or Owner Title and submits project information. "
            "APN / Parcel Number is a project location method."),
        "APN Parcel Number": "APN / Parcel Number is a project location method.",
        "Project List": "Users can search projects and review information and status.",
        "Building Address": "Enter an address determined by the Google Maps API.",
        "Login Page": "Enter your assigned username and password.",
    }

    class Retrieval:
        async def search(self, query):
            if broken:
                raise RuntimeError("gsk_do_not_report postgres://private:password@host/db")
            section = next((case.expected_section for case in answer_cases
                            if case.query in query), None)
            if section is None:
                return []
            return [RetrievalCandidate(uuid4(), uuid4(), "approved", "approved.md",
                                       corpus[section], section, None, {}, 0.9, 0.9)]

    class LLM:
        async def generate(self, *, system_prompt, user_prompt):
            section = next(section for section, content in corpus.items() if content in user_prompt)
            return LLMResponse(corpus[section], "fake-model", 100, 20, 120)

    retrieval = CallCounter(Retrieval(), "search")
    llm = CallCounter(LLM(), "generate")
    rag = CallCounter(RAGService(retrieval_service=retrieval, llm_client=llm), "answer")
    asta = AstaService(rag_service=rag)
    repository = MemoryRepository()
    cleanup = []

    @asynccontextmanager
    async def scope():
        conversation = ConversationService(None, responder=asta, repository=repository)
        try:
            yield conversation, await conversation.start_conversation()
        finally:
            cleanup.append(len(repository.messages))
            repository.messages.clear()

    return EvaluationServices(retrieval, rag, llm, asta, scope), cleanup


def report_for(results):
    return Report(run_id="test", started_at="test", suite_name="test", suite_sha256="test",
                  results=results, regressions=[RegressionResult(name=name, passed=True, tests=10)
                                                for name in ("python", "node")])


@pytest.mark.asyncio
async def test_runner_uses_real_rag_guardrails_and_conversation_with_fake_boundaries():
    suite = load_cases(GOLDEN)
    services, cleanup = fake_services(suite)
    results = await run_cases(suite, services)
    assert all(result.passed for result in results), [(r.id, r.checks) for r in results if not r.passed]
    assert cleanup == [10]
    assert services.llm.calls == 8  # Five answers and three supported conversation turns.
    assert results[-1].steps[1].observation.contextualized
    assert not results[-1].steps[2].observation.contextualized
    assert results[-1].steps[-1].observation.rag_calls == 0
    report = finalize_report(report_for(results), suite)
    assert report.status == "PASS"
    assert exit_status(report) == 0
    results[0].checks["ranking"] = False
    assert exit_status(finalize_report(report, suite)) == 1


@pytest.mark.asyncio
async def test_service_errors_fail_closed_and_do_not_expose_exception_text():
    suite = load_cases(GOLDEN)
    services, cleanup = fake_services(suite, broken=True)
    results = await run_cases(suite, services)
    report = finalize_report(report_for(results), suite)
    assert report.status == "FAIL"
    assert "gsk_" not in report.model_dump_json()
    assert cleanup  # The scope exits even on a failed turn.


@pytest.mark.asyncio
async def test_missing_results_or_failed_regressions_cannot_pass():
    suite = load_cases(GOLDEN)
    services, _ = fake_services(suite)
    results = await run_cases(suite, services)
    report = report_for(results[:-1])
    assert exit_status(finalize_report(report, suite)) == 1
    report.results = results
    report.regressions[0].passed = False
    assert exit_status(finalize_report(report, suite)) == 1
    assert exit_status(finalize_report(report_for([]), suite)) == 1


@pytest.mark.parametrize("name, expected", [
    ("APIConnectionError", "connection_error"), ("APITimeoutError", "timeout"),
    ("AuthenticationError", "provider_error"), ("ValueError", "service_error"),
])
def test_diagnostics_are_finite_codes(name, expected):
    error = type(name, (Exception,), {})("private data must never be shown")
    outer = RuntimeError("private outer error")
    outer.__cause__ = error
    assert classify_error(outer) == expected
