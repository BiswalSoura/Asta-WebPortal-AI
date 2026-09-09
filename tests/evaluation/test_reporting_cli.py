import json

import pytest
from pydantic import ValidationError

from app.evaluation.reporting import serialize_report, write_report
from app.evaluation.results import CaseResult, PipelineSummary
from scripts import run_evaluation
from tests.evaluation.test_cases import GOLDEN
from tests.evaluation.test_runner import fake_services, report_for


def test_report_round_trip_and_secret_safety(tmp_path):
    result = CaseResult(id="safe-id", category="guardrail", checks={"fixed_answer": True},
                        query="postgresql://user:password@host/db gsk_fakekey hf_fakekey "
                        "password=secret-value private-prompt-text plain-secret-value")
    report = report_for([result])
    text = serialize_report(report, ("private-prompt-text", "plain-secret-value"))
    assert all(value not in text for value in (
        "postgresql://", "gsk_fakekey", "hf_fakekey", "secret-value", "private-prompt-text"))
    data = json.loads(text)
    assert data["results"][0]["passed"] is True
    assert "answer" not in data["results"][0]
    path = tmp_path / "report.json"
    write_report(path, report, ("private-prompt-text", "plain-secret-value"))
    assert json.loads(path.read_text()) == data
    assert not path.with_suffix(".json.tmp").exists()


def test_settings_dto_rejects_arbitrary_credentials():
    with pytest.raises(ValidationError):
        PipelineSummary.model_validate({"database_url": "postgresql://secret"})


def test_invalid_cases_cli_exits_nonzero_and_writes_safe_failure(tmp_path, capsys):
    cases = tmp_path / "invalid.json"
    cases.write_text('{"secret": "gsk_never_echo"}')
    report = tmp_path / "report.json"
    assert run_evaluation.main(["--cases", str(cases), "--report", str(report)]) == 1
    data = json.loads(report.read_text())
    assert data["status"] == "FAIL"
    assert data["error_code"] == "invalid_cases"
    assert "gsk_never_echo" not in capsys.readouterr().out + report.read_text()


def test_cli_success_and_deliberate_failure(tmp_path, monkeypatch):
    from app.evaluation.runner import run_cases

    monkeypatch.setattr(run_evaluation, "run_regressions", lambda root: report_for([]).regressions)
    fail = False

    async def live(suite, report, progress):
        services, _ = fake_services(suite)
        report.results = await run_cases(suite, services, progress)
        if fail:
            report.results[0].checks["ranking"] = False

    monkeypatch.setattr(run_evaluation, "evaluate_live", live)
    path = tmp_path / "report.json"
    arguments = ["--cases", str(GOLDEN), "--report", str(path)]
    assert run_evaluation.main(arguments) == 0
    assert json.loads(path.read_text())["status"] == "PASS"
    fail = True
    assert run_evaluation.main(arguments) == 1
    assert json.loads(path.read_text())["status"] == "FAIL"


def test_runtime_error_is_safe_and_nonzero(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(run_evaluation, "run_regressions", lambda root: report_for([]).regressions)

    async def broken(*args):
        raise RuntimeError("gsk_never_echo internal prompt and password")

    monkeypatch.setattr(run_evaluation, "evaluate_live", broken)
    path = tmp_path / "report.json"
    assert run_evaluation.main(["--report", str(path)]) == 1
    assert json.loads(path.read_text())["error_code"] == "runtime_error"
    assert "gsk_never_echo" not in path.read_text() + capsys.readouterr().out
