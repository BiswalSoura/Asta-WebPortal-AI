"""Run M12: python -m scripts.run_evaluation (real database and Groq)."""

import argparse
import asyncio
import hashlib
import logging
import os
import subprocess
import sys
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from app.evaluation.cases import load_cases
from app.evaluation.regressions import run_regressions
from app.evaluation.reporting import write_report
from app.evaluation.results import PipelineSummary, Report
from app.evaluation.runner import exit_status, finalize_report, run_cases

ROOT = Path(__file__).resolve().parents[1]


async def evaluate_live(suite, report, progress):
    # Lazy imports keep case validation and CLI unit tests independent of model loading.
    from app.core.config import get_settings
    from app.database.session import get_engine, get_session_factory
    from app.evaluation.live import build_services, corpus_manifest

    settings = get_settings()
    report.settings_summary = PipelineSummary(**{
        "embedding_model": settings.embedding_model,
        "embedding_device": settings.embedding_device,
        "reranker_model": settings.reranker_model,
        "reranker_device": settings.reranker_device,
        "retrieval_top_k": settings.retrieval_top_k,
        "retrieval_final_k": settings.retrieval_final_k,
        "reranker_min_score": settings.reranker_min_score,
        "groq_model": settings.groq_model or "",
        "llm_temperature": settings.llm_temperature,
    })
    if any(case.category == "retrieval" and case.k > settings.retrieval_final_k
           for case in suite.cases):
        raise ValueError("Case K exceeds final retrieval window")
    if (settings.groq_model != "openai/gpt-oss-120b" or settings.llm_temperature != 0.0
            or settings.embedding_model != "BAAI/bge-small-en-v1.5"
            or settings.reranker_model != "cross-encoder/ms-marco-MiniLM-L-6-v2"
            or settings.embedding_device != "cpu" or settings.reranker_device != "cpu"):
        raise ValueError("Live configuration differs from the frozen M12 baseline")
    try:
        async with get_session_factory()() as session:
            try:
                report.corpus_sections, report.corpus_sha256 = await corpus_manifest(session)
                services = build_services(session)
                report.results = await run_cases(suite, services, progress)
            finally:
                await session.rollback()
    finally:
        await get_engine().dispose()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run the complete M12 quality gates.")
    parser.add_argument("--cases", type=Path, default=ROOT / "data/evaluation/golden_cases.json")
    parser.add_argument("--report", type=Path, default=None)
    arguments = parser.parse_args(argv)
    run_id = str(uuid4())
    destination = arguments.report or ROOT / f"data/evaluation/results/{run_id}.json"
    report = Report(run_id=run_id, started_at=datetime.now(timezone.utc).isoformat(),
                    suite_name="unvalidated", suite_sha256="")
    suite = None
    start = perf_counter()
    sensitive_values = ()
    terminal = sys.stdout
    previous_logging = logging.root.manager.disable
    try:
        try:
            suite = load_cases(arguments.cases)
            report.suite_name = suite.name
            report.suite_sha256 = hashlib.sha256(arguments.cases.read_bytes()).hexdigest()
        except Exception:
            report.error_code = "invalid_cases"
        if suite is not None:
            try:
                revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                          capture_output=True, text=True, timeout=10)
                if revision.returncode == 0 and len(revision.stdout.strip()) == 40:
                    report.baseline_commit = revision.stdout.strip()
            except Exception:
                pass  # Read-only Git is optional, never a blocker.
            print("Running mandatory Python and Node regression suites...", flush=True)
            report.regressions = run_regressions(ROOT)
            for regression in report.regressions:
                print(f"{regression.name}: {'PASS' if regression.passed else 'FAIL'} "
                      f"({regression.tests} tests)", flush=True)
            if not all(r.passed for r in report.regressions):
                report.error_code = "regression_failure"
            else:
                print("Running live evaluation; first model load can take longer...", flush=True)

                def progress(result):
                    diagnostic = f" ({result.error_code})" if result.error_code else ""
                    print(f"{result.id}: {'PASS' if result.passed else 'FAIL'}{diagnostic}",
                          file=terminal, flush=True)

                # Third-party debug output and exceptions must never reach the public CLI.
                logging.disable(logging.CRITICAL)
                with open(os.devnull, "w") as sink, redirect_stdout(sink), redirect_stderr(sink):
                    from app.core.config import get_settings
                    from app.prompts import ASTA_SYSTEM_PROMPT
                    from sqlalchemy.engine import make_url

                    settings = get_settings()
                    sensitive_values = tuple(filter(None, (
                        settings.groq_api_key, settings.database_url, settings.test_database_url,
                        make_url(settings.database_url).password if settings.database_url else None,
                        os.environ.get("HF_TOKEN"), os.environ.get("HUGGING_FACE_HUB_TOKEN"),
                        ASTA_SYSTEM_PROMPT,
                    )))
                    kwargs = {"loop_factory": asyncio.SelectorEventLoop} if sys.platform == "win32" else {}
                    asyncio.run(evaluate_live(suite, report, progress), **kwargs)
    except Exception:
        report.error_code = "runtime_error"
    finally:
        logging.disable(previous_logging)
    report.elapsed_seconds = perf_counter() - start
    finalize_report(report, suite)
    try:
        write_report(destination, report, sensitive_values)
    except Exception:
        print("FAIL: report could not be written safely.")
        return 1
    for category, summary in report.category_summary.items():
        print(f"{category}: {summary['passed']}/{summary['total']} passed")
    metrics = report.retrieval_metrics
    for group, values in report.robustness_metrics.items():
        print(f"{group}: {values['passed']}/{values['total']} passed")
    print(f"Top-1={metrics['top1_accuracy']:.3f} Recall@K={metrics['recall_at_k']:.3f} "
          f"MRR={metrics['mrr']:.3f}")
    print(f"Overall {report.status}; JSON report written. Run ID: {run_id}")
    return exit_status(report)


if __name__ == "__main__":
    raise SystemExit(main())
