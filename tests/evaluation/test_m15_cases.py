from pathlib import Path

from app.evaluation.cases import AnswerCase, ConversationCase, load_cases
from app.evaluation.results import CaseResult, Report
from app.evaluation.runner import finalize_report

ROOT = Path(__file__).resolve().parents[2]


def test_m15_retains_every_original_case_and_all_robustness_groups():
    original = load_cases(ROOT / 'data/evaluation/golden_cases.json')
    expanded = load_cases(ROOT / 'data/evaluation/m15_robustness_cases.json')
    by_id = {c.id: c for c in expanded.cases}
    assert all(by_id[c.id] == c for c in original.cases)
    entries = [e for c in expanded.cases for e in (c.steps if isinstance(c, ConversationCase) else [c])]
    groups = {e.robustness_group for e in entries if isinstance(e, AnswerCase)} - {None}
    assert groups == {'clean_supported', 'paraphrase', 'casual_filler', 'typo_grammar',
                      'contextual_followup', 'ambiguous_clarification', 'gibberish_clarification',
                      'obfuscated_injection', 'understood_unsupported'}
    assert {e.expected_section for e in entries if isinstance(e, AnswerCase) and e.robustness_group} >= {
        'Create New Project', 'APN Parcel Number', 'Project List', 'Building Address', 'Login Page'}


def test_missing_robustness_results_count_as_failures():
    suite = load_cases(ROOT / 'data/evaluation/m15_robustness_cases.json')
    report = Report(run_id='test', started_at='test', suite_name=suite.name, suite_sha256='test')
    report.results = [CaseResult(id='m15-create-0', category='supported_answer', checks={'ok': True})]
    finalize_report(report, suite)
    assert report.robustness_metrics['clean_supported']['pass_rate'] == 1.0
    assert report.robustness_metrics['obfuscated_injection']['pass_rate'] == 0.0
    assert report.status == 'FAIL'
