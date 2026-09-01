from collections.abc import Callable, Sequence
from dataclasses import dataclass
from time import perf_counter


@dataclass(frozen=True)
class RetrievalEvaluation:
    query_id: str
    recall_at_k: float
    precision_at_k: float
    citation_match: float
    source_coverage: float
    latency_ms: float | None = None


def evaluate_ranked_sources(
    *,
    query_id: str,
    expected_sources: set[str],
    ranked_sources: Sequence[str],
    k: int,
    latency_ms: float | None = None,
) -> RetrievalEvaluation:
    if not query_id.strip() or not expected_sources or not 1 <= k <= 100:
        raise ValueError("Evaluation query, expected sources and k are required")
    top_k = list(ranked_sources[:k])
    hits = sum(source in expected_sources for source in top_k)
    unique_hits = len(set(top_k).intersection(expected_sources))
    return RetrievalEvaluation(
        query_id=query_id,
        recall_at_k=unique_hits / len(expected_sources),
        precision_at_k=hits / len(top_k) if top_k else 0.0,
        citation_match=unique_hits / len(expected_sources),
        source_coverage=len(set(ranked_sources).intersection(expected_sources))
        / len(expected_sources),
        latency_ms=latency_ms,
    )


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
