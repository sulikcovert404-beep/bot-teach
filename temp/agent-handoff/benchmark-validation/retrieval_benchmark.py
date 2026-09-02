"""Controlled, provider-neutral benchmark runner for retrieval implementations."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

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
        for case in cases:
            ranked = retrieve(case, k)
            evaluations.append(
                evaluate_ranked_sources(
                    query_id=case.query_id,
                    expected_sources=set(case.expected_sources),
                    ranked_sources=[chunk.source_id for chunk in ranked],
                    k=k,
                    expects_no_source=case.expected_state == "no_source",
                    expects_conflict=case.expected_state == "conflict",
                )
            )
        results.append(BenchmarkResult(provider, tuple(evaluations)))
    return tuple(results)
