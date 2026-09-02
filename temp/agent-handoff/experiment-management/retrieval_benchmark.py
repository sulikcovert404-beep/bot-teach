"""Controlled, provider-neutral benchmark runner for retrieval implementations."""

from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
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


@dataclass(frozen=True)
class BenchmarkRunArtifact:
    """Portable metadata envelope for comparing benchmark executions."""

    run_id: str
    dataset_version: str
    retriever_version: str
    timestamp: str
    execution_metadata: dict[str, Any]
    metric_snapshot: dict[str, dict[str, float]]
    results: tuple[dict[str, Any], ...]

    def to_report(self) -> dict[str, Any]:
        return asdict(self)


def persist_run_artifact(
    results: Sequence[BenchmarkResult],
    *,
    dataset_version: str,
    retriever_version: str,
    execution_metadata: dict[str, Any] | None = None,
    run_id: str | None = None,
    timestamp: str | None = None,
) -> BenchmarkRunArtifact:
    """Build a JSON-serializable artifact without writing to a provider-specific store."""
    if not dataset_version.strip() or not retriever_version.strip():
        raise ValueError("Dataset and retriever versions are required")
    generated_at = timestamp or datetime.now(UTC).isoformat()
    stable_run_id = run_id or f"{dataset_version}-{generated_at.replace(':', '').replace('+00:00', 'Z')}"
    snapshots: dict[str, dict[str, float]] = {}
    reports: list[dict[str, Any]] = []
    for result in results:
        report = result.to_report()
        snapshots[result.provider] = report["aggregate"]
        reports.append(report)
    return BenchmarkRunArtifact(
        run_id=stable_run_id,
        dataset_version=dataset_version,
        retriever_version=retriever_version,
        timestamp=generated_at,
        execution_metadata=dict(execution_metadata or {}),
        metric_snapshot=snapshots,
        results=tuple(reports),
    )


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
