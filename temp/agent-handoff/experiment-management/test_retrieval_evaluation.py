import pytest

from app.services.retrieval_evaluation import (
    EvaluationCase,
    FaithfulnessEvaluation,
    evaluate_ranked_sources,
    measure_retrieval,
    normalize_persian_text,
    stratify_results,
)


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


def test_evaluation_reports_mrr_and_no_source_accuracy() -> None:
    result = evaluate_ranked_sources(
        query_id="q1", expected_sources={"a"}, ranked_sources=["noise", "a"], k=2
    )
    assert result.reciprocal_rank == 0.5
    empty = evaluate_ranked_sources(
        query_id="q2", expected_sources=set(), ranked_sources=[], k=2, expects_no_source=True
    )
    assert empty.no_source_correct is True


def test_evaluation_case_validates_dataset_contract() -> None:
    case = EvaluationCase(
        query_id="q1", question="فصل اول چیست؟", expected_sources=frozenset({"book:p1"}),
        subject="فیزیک", grade="دهم", chapter="۱", difficulty="easy",
        expected_answer="پاسخ نمونه", paraphrase_variants=("صورت دیگر",), provenance="book-v1"
    )
    assert case.expected_sources == frozenset({"book:p1"})
    assert case.expected_answer == "پاسخ نمونه"
    with pytest.raises(ValueError):
        EvaluationCase(query_id="q2", question="نامشخص", expected_sources=frozenset())


def test_ndcg_and_r_precision_support_graded_relevance() -> None:
    result = evaluate_ranked_sources(
        query_id="q1", expected_sources={"exact", "related"},
        ranked_sources=["related", "exact"], k=2,
        relevance_grades={"exact": 3, "related": 1},
    )
    assert 0 < result.ndcg_at_k <= 1
    assert result.r_precision == 1.0


def test_citation_accuracy_is_separate_from_retrieval_match() -> None:
    result = evaluate_ranked_sources(
        query_id="q1", expected_sources={"a"}, ranked_sources=["a"], k=1,
        cited_sources=["wrong"],
    )
    assert result.recall_at_k == 1.0
    assert result.citation_match == 0.0


def test_persian_normalization_and_faithfulness_contract() -> None:
    assert normalize_persian_text("ك تاب\u200c  ي") == "ک تاب‌ ی"
    contract = FaithfulnessEvaluation(("c1",), frozenset(), frozenset())
    assert contract.scoring_status == "not_scored"


def test_stratified_report_groups_by_metadata() -> None:
    case = EvaluationCase(query_id="q1", question="سوال", expected_sources=frozenset({"a"}), grade="دهم", subject="فیزیک", chapter="۱")
    result = evaluate_ranked_sources(query_id="q1", expected_sources={"a"}, ranked_sources=["a"], k=1)
    report = stratify_results([case], [result])
    assert report[("دهم", "فیزیک", "۱")]["mrr"] == 1.0
