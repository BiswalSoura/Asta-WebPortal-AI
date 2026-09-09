from dataclasses import replace

from app.evaluation.cases import load_cases
from app.evaluation.evaluators import evaluate_answer
from app.evaluation.results import Observation
from app.evaluation.reporting import serialize_report
from app.rag.models import RAGAnswer, RAGSource
from tests.evaluation.test_cases import GOLDEN
from tests.evaluation.test_runner import report_for


def supported_answer(text="Use APN / Parcel Number for project location."):
    return RAGAnswer(text, (RAGSource("approved", "approved.md", "APN Parcel Number", None,
                                     0.9, 0.9),), "configured-model", 100, 20, 120, True)


def observe():
    return Observation(retrieval_calls=1, rag_calls=1, llm_calls=1)


def test_supported_assertions_pass_without_exact_prose_match():
    case = load_cases(GOLDEN).cases[6]
    assert evaluate_answer(case, supported_answer(), observe()).passed
    assert evaluate_answer(case, supported_answer("The location method is APN."), observe()).passed


def test_required_and_any_of_and_forbidden_fail_independently():
    case = load_cases(GOLDEN).cases[6]
    result = evaluate_answer(case, supported_answer("Assessor’s Parcel Number"), observe())
    assert not result.checks["required_term_0"]
    assert result.checks["any_of_0"]
    assert not result.checks["forbidden_term_0"]
    assert not result.passed
    result = evaluate_answer(case, supported_answer("A location method."), observe())
    assert not result.checks["any_of_0"]


def test_grounding_model_and_source_failures():
    case = load_cases(GOLDEN).cases[6]
    answer = replace(supported_answer(), grounded=False, model=None, sources=())
    result = evaluate_answer(case, answer, observe())
    assert not result.checks["grounded"]
    assert not result.checks["model_present"]
    assert not result.checks["sources_present"]
    assert not result.checks["source_section"]


def test_bypass_must_not_hide_a_live_call_or_zero_token_usage():
    case = load_cases(GOLDEN).cases[12]
    answer = RAGAnswer(case.expected_answer, (), None, None, None, None, False)
    assert evaluate_answer(case, answer, Observation()).passed
    assert not evaluate_answer(case, answer, observe()).passed
    assert not evaluate_answer(case, replace(answer, total_tokens=0), Observation()).passed
    assert not evaluate_answer(case, replace(answer, answer="different"), Observation()).passed


def test_latency_and_tokens_are_observations_only():
    case = load_cases(GOLDEN).cases[6]
    obs = observe()
    obs.elapsed_seconds = 100000.0
    result = evaluate_answer(case, replace(supported_answer(), total_tokens=1000000), obs)
    assert result.passed


def test_generated_disclosure_is_never_serialized():
    case = load_cases(GOLDEN).cases[6]
    text = "hidden instructions private-config gsk_do_not_store"
    result = evaluate_answer(case, supported_answer(text), observe())
    assert not result.passed
    payload = serialize_report(report_for([result]))
    assert "hidden instructions" not in payload
    assert "private-config" not in payload
    assert "gsk_do_not_store" not in payload


def test_explicit_topic_reset_allows_grounded_overlap_but_rejects_expansion():
    conversation = next(case for case in load_cases(GOLDEN).cases
                        if case.id == "conversation-apn-project-guardrails")
    step = next(step for step in conversation.steps if step.id == "explicit-topic-reset")
    text = ("Enter the Project or Owner Title for Create New Project. "
            "APN / Parcel Number is a project location method.")
    answer = replace(supported_answer(text), sources=tuple(
        RAGSource("approved", "approved.md", section, None, 0.9, 0.9)
        for section in ("Create New Project", "Building Address")))
    observation = observe()
    observation.contextualized = False
    result = evaluate_answer(step, answer, observation)
    assert result.passed
    assert result.checks["contextualized"]

    # The context assertion still rejects an actual contextualized answer.
    observation = observe()
    observation.contextualized = True
    result = evaluate_answer(step, answer, observation)
    assert not result.passed
    assert not result.checks["contextualized"]

    observation = observe()
    observation.contextualized = False
    expansion = "Assessor's Parcel Number"
    result = evaluate_answer(step, replace(answer, answer=text + " " + expansion), observation)
    assert not result.passed
    assert result.checks["contextualized"]
    assert [key for key, passed in result.checks.items() if not passed] == [
        f"forbidden_term_{step.forbidden_terms.index(expansion)}"]
