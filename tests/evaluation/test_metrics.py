import pytest

from app.evaluation.metrics import aggregate_retrieval, contains, retrieval_metrics, section_rank


@pytest.mark.parametrize("sections, rank, top1, recall, rr", [
    (["APN Parcel Number", "Building Address"], 1, True, 1.0, 1.0),
    (["Building Address", "APN Parcel Number"], 2, False, 1.0, 0.5),
    ([None, "Other", "APN Parcel Number"], 3, False, 0.0, 1/3),
    (["Other"], None, False, 0.0, 0.0),
    ([], None, False, 0.0, 0.0),
])
def test_rank_and_metrics(sections, rank, top1, recall, rr):
    result = retrieval_metrics(sections, "APN Parcel Number", 2)
    assert result.expected_section_rank == rank
    assert result.top1_correct is top1
    assert result.recall_at_k == recall
    assert result.reciprocal_rank == pytest.approx(rr)


def test_aggregate_metrics_and_empty_inputs():
    items = [retrieval_metrics(s, "Topic", 2) for s in [["Topic"], ["X", "Topic"], []]]
    result = aggregate_retrieval(items)
    assert result["top1_accuracy"] == pytest.approx(1/3)
    assert result["recall_at_k"] == pytest.approx(2/3)
    assert result["mrr"] == pytest.approx(0.5)
    assert aggregate_retrieval([])["mrr"] == 0
    with pytest.raises(ValueError):
        retrieval_metrics([], "Topic", 0)


def test_phrase_matching_is_case_punctuation_and_boundary_aware():
    assert contains("Enter PROJECT / OWNER TITLE.", "Project Owner Title")
    assert contains("Assessor’s Parcel Number", "Assessor's Parcel Number")
    assert not contains("apnea", "APN")
    assert section_rank(["APN / Parcel Number"], "apn parcel number") == 1
    assert section_rank(["APN Parcel Number Extra"], "APN Parcel Number") is None
