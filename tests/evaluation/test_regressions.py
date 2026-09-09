from pathlib import Path
from types import SimpleNamespace

import pytest

from app.evaluation.regressions import run_regressions


@pytest.mark.parametrize("failed, skipped, returncode, expected", [
    (0, 0, 0, True), (1, 0, 1, False), (0, 1, 0, False), (0, 0, 2, False),
])
def test_regression_subprocess_gates(tmp_path, monkeypatch, failed, skipped, returncode, expected):
    def run(command, **kwargs):
        if "pytest" in command:
            destination = next(part.split("=", 1)[1] for part in command if part.startswith("--junitxml"))
            Path(destination).write_text(
                f'<testsuites><testsuite tests="5" failures="{failed}" errors="0" '
                f'skipped="{skipped}"/></testsuites>')
            return SimpleNamespace(returncode=returncode, stdout="private output")
        return SimpleNamespace(returncode=0, stdout=(
            "# tests 10\n# fail 0\n# cancelled 0\n# skipped 0\n# todo 0\n"))

    monkeypatch.setattr("app.evaluation.regressions.subprocess.run", run)
    results = run_regressions(tmp_path)
    assert results[0].passed is expected
    assert results[1].passed
    assert all("private output" not in result.model_dump_json() for result in results)


def test_missing_runtime_fails_safely(tmp_path, monkeypatch):
    def fail(*args, **kwargs):
        raise OSError("private connection string")
    monkeypatch.setattr("app.evaluation.regressions.subprocess.run", fail)
    assert all(not result.passed for result in run_regressions(tmp_path))
