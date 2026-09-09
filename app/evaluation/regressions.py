"""Run mandatory existing suites; discard raw subprocess output from reports."""

import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from app.evaluation.results import RegressionResult


def run_regressions(root: Path) -> list[RegressionResult]:
    cache = root / ".cache" / "evaluation"
    cache.mkdir(parents=True, exist_ok=True)
    results = []
    with tempfile.TemporaryDirectory(dir=cache) as directory:
        work = Path(directory)
        commands = {
            "python": [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                       f"--basetemp={work / 'tmp'}", f"--junitxml={work / 'pytest.xml'}"],
            "node": ["node", "--test", "--test-reporter=tap", "frontend/tests/chat-client.test.mjs"],
        }
        for name, command in commands.items():
            try:
                process = subprocess.run(command, cwd=root, capture_output=True, text=True,
                                         encoding="utf-8", errors="replace", timeout=300)
                if name == "python":
                    suites = ET.parse(work / "pytest.xml").getroot().iter("testsuite")
                    counts = {key: 0 for key in ("tests", "failures", "errors", "skipped")}
                    for suite in suites:
                        for key in counts:
                            counts[key] += int(suite.get(key, "0"))
                else:
                    def count(label):
                        match = re.search(rf"^# {label} (\d+)$", process.stdout, re.MULTILINE)
                        if match is None:
                            raise ValueError("Missing test totals")
                        return int(match.group(1))
                    counts = dict(tests=count("tests"), failures=count("fail"),
                                  errors=count("cancelled"), skipped=count("skipped") + count("todo"))
                passed = process.returncode == 0 and counts["tests"] > 0 and not any(
                    counts[key] for key in ("failures", "errors", "skipped"))
                results.append(RegressionResult(name=name, passed=passed, **counts))
            except Exception:
                results.append(RegressionResult(name=name, passed=False, errors=1))
    return results
