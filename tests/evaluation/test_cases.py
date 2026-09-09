import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.evaluation.cases import CaseSuite, load_cases

GOLDEN = Path(__file__).resolve().parents[2] / "data/evaluation/golden_cases.json"


def test_golden_case_parsing():
    suite = load_cases(GOLDEN)
    assert len(suite.cases) == 17
    assert suite.cases[0].k == 4
    assert suite.cases[-1].steps[1].expected_contextualized is True


@pytest.mark.parametrize("change", [
    lambda d: d.update(schema_version=2),
    lambda d: d.update(unexpected="field"),
    lambda d: d.update(cases=[]),
    lambda d: d["cases"].append(copy.deepcopy(d["cases"][0])),
    lambda d: d["cases"].pop(),
    lambda d: d["cases"][0].update(query=" "),
    lambda d: d["cases"][0].update(k=0),
    lambda d: d["cases"][0].update(k="4"),
    lambda d: d["cases"][0].update(max_rank=2),
    lambda d: d["cases"][0].update(max_rank=5, ambiguity_reason="explanation"),
    lambda d: d["cases"][5].update(expected_sources=False),
    lambda d: d["cases"][5].update(expected_answer="brittle generated answer"),
    lambda d: d["cases"][5].update(required_any_of=[[]]),
    lambda d: d["cases"][5].update(required_terms=["..."]),
    lambda d: d["cases"][5].update(required_terms=["role"], forbidden_terms=["ROLE"]),
    lambda d: d["cases"][5].update(required_any_of=[["role"]], forbidden_terms=["role"]),
    lambda d: d["cases"][10].update(expected_model=True),
    lambda d: d["cases"][10].pop("expected_answer"),
    lambda d: d["cases"][-1]["steps"][0].update(expected_contextualized=True),
    lambda d: d["cases"][-1]["steps"][1].pop("expected_contextualized"),
    lambda d: d["cases"][-1]["steps"][1].update(id="parcel-start"),
    lambda d: d["cases"][-1]["steps"][-1].update(expected_contextualized=True),
])
def test_invalid_cases_rejected(change):
    data = json.loads(GOLDEN.read_text())
    change(data)
    with pytest.raises(ValidationError):
        CaseSuite.model_validate(data)


def test_documented_ambiguity_is_explicit():
    data = json.loads(GOLDEN.read_text())
    data["cases"][0].update(max_rank=2, ambiguity_reason="Two approved sections define this topic")
    assert CaseSuite.model_validate(data).cases[0].max_rank == 2


def test_duplicate_json_keys_rejected(tmp_path):
    path = tmp_path / "cases.json"
    path.write_text('{"schema_version": 1, "schema_version": 1}')
    with pytest.raises(ValueError, match="Duplicate JSON"):
        load_cases(path)
