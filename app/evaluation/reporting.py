"""Summary-only JSON with defense-in-depth redaction at the serialization boundary."""

import json
import re
from pathlib import Path

from app.evaluation.results import Report

SECRET_PATTERN = re.compile(
    r"(?:[a-z][a-z0-9+.-]*://[^\s]+|\b(?:gsk_|hf_|sk-)[A-Za-z0-9_-]+|"
    r"(?:password|api[_ -]?key|token|secret)\s*[:=]\s*\S+)", re.IGNORECASE
)


def serialize_report(report: Report, sensitive_values: tuple[str, ...] = ()) -> str:
    def clean(value):
        if isinstance(value, str):
            for secret in sorted(filter(None, sensitive_values), key=len, reverse=True):
                value = value.replace(secret, "[REDACTED]")
            return SECRET_PATTERN.sub("[REDACTED]", value)
        if isinstance(value, list):
            return [clean(item) for item in value]
        if isinstance(value, dict):
            return {clean(key): clean(item) for key, item in value.items()}
        return value

    data = report.model_dump(mode="json")
    # Properties are intentionally computed, never trusted from input.
    def add_status(result, model):
        result["passed"] = model.passed
        for child, child_model in zip(result["steps"], model.steps, strict=True):
            add_status(child, child_model)
    for result, model in zip(data["results"], report.results, strict=True):
        add_status(result, model)
    return json.dumps(clean(data), ensure_ascii=False, indent=2, allow_nan=False) + "\n"


def write_report(path: Path, report: Report, sensitive_values: tuple[str, ...] = ()) -> None:
    payload = serialize_report(report, sensitive_values)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(payload, encoding="utf-8")
    temporary.replace(path)
