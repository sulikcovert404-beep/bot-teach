"""Controlled, provider-neutral benchmark runner for retrieval implementations."""

from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from time import perf_counter
from typing import Any

from app.services.rag import SourceChunk
from app.services.retrieval_evaluation import (
    EvaluationCase,
    RetrievalEvaluation,
    evaluate_ranked_sources,
    normalize_persian_text,
)

RetrieverFn = Callable[[EvaluationCase, int], Sequence[SourceChunk]]


@dataclass(frozen=True)
class BenchmarkResult:
    provider: str
    evaluations: tuple[RetrievalEvaluation, ...]
    raw_cases: tuple[dict[str, Any], ...] = ()

    def to_report(self) -> dict[str, Any]:
        """Return a JSON-serializable report with per-case evidence."""
        return {
            "provider": self.provider,
            "aggregate": {
                "recall_at_k": _mean(item.recall_at_k for item in self.evaluations),
                "precision_at_k": _mean(item.precision_at_k for item in self.evaluations),
                "mrr": _mean(item.reciprocal_rank for item in self.evaluations),
                "ndcg_at_k": _mean(item.ndcg_at_k for item in self.evaluations),
            },
            "evaluations": [asdict(item) for item in self.evaluations],
            "raw_cases": list(self.raw_cases),
        }


def _mean(values: Any) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def lexical_retrieve(
    chunks: Sequence[SourceChunk], case: EvaluationCase, limit: int
) -> list[SourceChunk]:
    """Return deterministic token-overlap ranking as a lexical baseline."""
    query_tokens = set(normalize_persian_text(case.question).split())
    ranked = sorted(
        chunks,
        key=lambda chunk: (
            -len(query_tokens.intersection(set(normalize_persian_text(chunk.text).split()))),
            chunk.source_id,
            chunk.page or 0,
        ),
    )
    return ranked[:limit]


def run_benchmark(
    cases: Sequence[EvaluationCase], retrievers: dict[str, RetrieverFn], *, k: int = 5
) -> tuple[BenchmarkResult, ...]:
    """Run identical cases against injected retrievers for comparable metrics."""
    if not cases or not retrievers:
        raise ValueError("Cases and retrievers are required")
    results: list[BenchmarkResult] = []
    for provider, retrieve in retrievers.items():
        evaluations: list[RetrievalEvaluation] = []
        raw_cases: list[dict[str, Any]] = []
        for case in cases:
            started = perf_counter()
            ranked = retrieve(case, k)
            latency_ms = (perf_counter() - started) * 1_000
            ranked_ids = [chunk.source_id for chunk in ranked]
            evaluations.append(
                evaluate_ranked_sources(
                    query_id=case.query_id,
                    expected_sources=set(case.expected_sources),
                    ranked_sources=ranked_ids,
                    k=k,
                    latency_ms=latency_ms,
                    expects_no_source=case.expected_state == "no_source",
                    expects_conflict=case.expected_state == "conflict",
                )
            )
            raw_cases.append(
                {
                    "query_id": case.query_id,
                    "query": case.question,
                    "retriever": provider,
                    "retrieved_source_ids": ranked_ids,
                    "rank": {str(index): source_id for index, source_id in enumerate(ranked_ids, 1)},
                    "scores": {str(index): chunk.score for index, chunk in enumerate(ranked, 1)},
                    "filters": {"grade": case.grade, "subject": case.subject, "chapter": case.chapter},
                    "latency_ms": latency_ms,
                    "expected_sources": sorted(case.expected_sources),
                    "metrics": asdict(evaluations[-1]),
                }
            )
        results.append(BenchmarkResult(provider, tuple(evaluations), tuple(raw_cases)))
    return tuple(results)
