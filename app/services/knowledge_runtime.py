"""Schema-neutral qualification helpers for the staging knowledge runtime.

The module deliberately operates on immutable retrieval candidates.  It is
usable by a database or vector adapter without inventing a second approval
schema, and applies access scope before ranking candidates.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from app.services.persian_text import normalize_persian_text


@dataclass(frozen=True)
class KnowledgeCandidate:
    text: str
    source_id: str
    chunk_id: int
    tenant_id: str
    classroom_id: int
    grade: str
    review_state: str
    publication_state: str
    vector_sync_state: str = "VECTOR_SYNCED"
    page: int | None = None

    def eligible_for(self, *, tenant_id: str, classroom_id: int, grade: str) -> bool:
        return (
            self.tenant_id == tenant_id
            and self.classroom_id == classroom_id
            and self.grade == grade
            and self.review_state == "APPROVED"
            and self.publication_state == "PUBLISHED"
            and self.vector_sync_state == "VECTOR_SYNCED"
        )


@dataclass(frozen=True)
class QualifiedEvidence:
    candidate: KnowledgeCandidate
    score: float


def retrieve_scoped(
    query: str,
    candidates: Iterable[KnowledgeCandidate],
    *,
    tenant_id: str,
    classroom_id: int,
    grade: str,
    limit: int = 5,
) -> tuple[QualifiedEvidence, ...]:
    """Filter by all publication/access invariants before lexical ranking."""
    if not query.strip() or limit < 1:
        return ()
    normalized_query = normalize_persian_text(query).casefold()
    terms = {term for term in normalized_query.split() if term}
    eligible = (
        candidate
        for candidate in candidates
        if candidate.eligible_for(
            tenant_id=tenant_id, classroom_id=classroom_id, grade=grade
        )
    )
    ranked: list[QualifiedEvidence] = []
    for candidate in eligible:
        normalized_text = normalize_persian_text(candidate.text).casefold()
        score = sum(term in normalized_text for term in terms) / max(len(terms), 1)
        if score > 0:
            ranked.append(QualifiedEvidence(candidate, score))
    ranked.sort(key=lambda item: (-item.score, item.candidate.chunk_id))
    return tuple(ranked[:limit])
