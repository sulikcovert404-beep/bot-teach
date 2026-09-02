from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from math import log2
from time import perf_counter
from typing import Literal


@dataclass(frozen=True)
class EvaluationCase:
    """Provider-neutral, serializable contract for one retrieval benchmark query."""

    query_id: str
    question: str
    expected_sources: frozenset[str] = frozenset()
    subject: str | None = None
    grade: str | None = None
    chapter: str | None = None
    difficulty: Literal["easy", "medium", "hard"] | None = None
    expects_no_source: bool = False
    expects_conflict: bool = False
    dataset_version: str = "v1"
    relevance_type: Literal["exact", "related", "none"] = "exact"
    expected_state: Literal["sufficient", "no_source", "conflict"] = "sufficient"

    def __post_init__(self) -> None:
        if not self.dataset_version.strip() or not self.query_id.strip() or not self.question.strip():
            raise ValueError("Evaluation query id and question are required")
        if (self.expects_no_source or self.expected_state == "no_source") and self.expected_sources:
            raise ValueError("No-source cases cannot define expected sources")
        if not self.expects_no_source and self.expected_state != "no_source" and not self.expected_sources:
            raise ValueError("Expected sources are required for sourced cases")


@dataclass(frozen=True)
class RetrievalEvaluation:
    query_id: str
    recall_at_k: float
    precision_at_k: float
    citation_match: float
    source_coverage: float
    reciprocal_rank: float = 0.0
    no_source_correct: bool | None = None
    conflict_detected: bool | None = None
    ndcg_at_k: float = 0.0
    r_precision: float = 0.0
    latency_ms: float | None = None


def evaluate_ranked_sources(
    *,
    query_id: str,
    expected_sources: set[str],
    ranked_sources: Sequence[str],
    k: int,
    latency_ms: float | None = None,
    expects_no_source: bool = False,
    expects_conflict: bool = False,
    conflict_detected: bool | None = None,
    relevance_grades: Mapping[str, int] | None = None,
) -> RetrievalEvaluation:
    if not query_id.strip() or (not expected_sources and not expects_no_source) or not 1 <= k <= 100:
        raise ValueError("Evaluation query, expected sources and k are required")
    top_k = list(ranked_sources[:k])
    hits = sum(source in expected_sources for source in top_k)
    unique_hits = len(set(top_k).intersection(expected_sources))
    first_hit = next((index + 1 for index, source in enumerate(top_k) if source in expected_sources), None)
    reciprocal_rank = 1 / first_hit if first_hit else 0.0
    no_source_correct = (not top_k) == expects_no_source if expects_no_source else None
    grades = relevance_grades or {source: int(source in expected_sources) for source in top_k}
    dcg = sum((grades.get(source, 0)) / log2(index + 2) for index, source in enumerate(top_k))
    ideal = sorted((value for value in grades.values() if value > 0), reverse=True)[:k]
    ideal_dcg = sum(value / log2(index + 2) for index, value in enumerate(ideal))
    ndcg_at_k = dcg / ideal_dcg if ideal_dcg else 0.0
    r_precision = (
        sum(source in expected_sources for source in ranked_sources[: len(expected_sources)])
        / len(expected_sources)
        if expected_sources
        else 0.0
    )
    return RetrievalEvaluation(
        query_id=query_id,
        recall_at_k=unique_hits / len(expected_sources) if expected_sources else 0.0,
        precision_at_k=hits / len(top_k) if top_k else 0.0,
        citation_match=unique_hits / len(expected_sources) if expected_sources else 0.0,
        source_coverage=(
            len(set(ranked_sources).intersection(expected_sources)) / len(expected_sources)
            if expected_sources
            else 0.0
        ),
        reciprocal_rank=reciprocal_rank,
        no_source_correct=no_source_correct,
        conflict_detected=conflict_detected if expects_conflict else None,
        ndcg_at_k=ndcg_at_k,
        r_precision=r_precision,
        latency_ms=latency_ms,
    )


@dataclass(frozen=True)
class FaithfulnessEvaluation:
    """Contract boundary for answer faithfulness; scoring is intentionally deferred."""

    claim_ids: tuple[str, ...]
    supported_claim_ids: frozenset[str]
    citation_source_ids: frozenset[str]
    scoring_status: Literal["not_scored"] = "not_scored"


def normalize_persian_text(text: str) -> str:
    """Normalize common Persian/Arabic and whitespace variants for benchmark fixtures."""
    return " ".join(
        text.replace("ي", "ی").replace("ى", "ی").replace("ك", "ک")
        .replace("ۀ", "هٔ").replace("ـ", "").split()
    )


def stratify_results(cases: Sequence[EvaluationCase], results: Sequence[RetrievalEvaluation]) -> dict[tuple[str | None, str | None, str | None], dict[str, float]]:
    """Aggregate benchmark metrics by grade, subject and chapter without thresholds."""
    if len(cases) != len(results):
        raise ValueError("Cases and results must have equal lengths")
    grouped: dict[tuple[str | None, str | None, str | None], list[RetrievalEvaluation]] = {}
    for case, result in zip(cases, results):
        grouped.setdefault((case.grade, case.subject, case.chapter), []).append(result)
    return {
        key: {
            "recall_at_k": sum(item.recall_at_k for item in values) / len(values),
            "precision_at_k": sum(item.precision_at_k for item in values) / len(values),
            "mrr": sum(item.reciprocal_rank for item in values) / len(values),
            "ndcg_at_k": sum(item.ndcg_at_k for item in values) / len(values),
        }
        for key, values in grouped.items()
    }


def measure_retrieval(
    retrieve: Callable[[], Sequence[str]],
    *,
    query_id: str,
    expected_sources: set[str],
    k: int,
) -> RetrievalEvaluation:
    started = perf_counter()
    ranked_sources = retrieve()
    elapsed_ms = (perf_counter() - started) * 1_000
    return evaluate_ranked_sources(
        query_id=query_id,
        expected_sources=expected_sources,
        ranked_sources=ranked_sources,
        k=k,
        latency_ms=elapsed_ms,
    )
