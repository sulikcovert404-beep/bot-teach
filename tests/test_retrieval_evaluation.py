import pytest

from app.services.retrieval_evaluation import evaluate_ranked_sources, measure_retrieval


def test_evaluation_reports_recall_precision_and_citation() -> None:
    result = evaluate_ranked_sources(
        query_id="q1",
        expected_sources={"a"},
        ranked_sources=["a", "noise"],
        k=2,
    )
    assert result.recall_at_k == 1.0
    assert result.precision_at_k == 0.5
    assert result.citation_match == 1.0
    assert result.source_coverage == 1.0


def test_evaluation_does_not_count_duplicate_sources_as_extra_recall() -> None:
    result = evaluate_ranked_sources(
        query_id="q1", expected_sources={"a", "b"}, ranked_sources=["a", "a"], k=2
    )
    assert result.recall_at_k == 0.5
    assert result.precision_at_k == 1.0


def test_measure_retrieval_records_latency() -> None:
    result = measure_retrieval(
        lambda: ["source"], query_id="q1", expected_sources={"source"}, k=1
    )
    assert result.latency_ms is not None
    assert result.latency_ms >= 0


def test_evaluation_rejects_invalid_contract() -> None:
    with pytest.raises(ValueError):
        evaluate_ranked_sources(query_id="", expected_sources={"a"}, ranked_sources=[], k=1)
