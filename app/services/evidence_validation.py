"""Provider-neutral evidence decision contract.

This module is intentionally pure: it does not call a retriever or an AI
provider.  Runtime integration is gated separately.
"""

from collections.abc import Sequence
from dataclasses import asdict, dataclass
from enum import StrEnum
from json import dumps

from app.services.rag import GroundingState, RetrievedChunk


class EvidenceOutcome(StrEnum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    ABSTAIN = "ABSTAIN"
    CONFLICT = "CONFLICT"
    RETRIEVAL_FAILURE = "RETRIEVAL_FAILURE"


@dataclass(frozen=True)
class EvidenceProvenance:
    source_identity: str
    content_digest: str
    source_version: str
    index_generation: str
    scope: str
    normalization_version: str
    trace_id: str

    def __post_init__(self) -> None:
        if not all(value.strip() for value in (
            self.source_identity, self.content_digest, self.source_version,
            self.index_generation, self.scope, self.normalization_version,
            self.trace_id,
        )):
            raise ValueError("Evidence provenance fields are required")


@dataclass(frozen=True)
class EvidenceDecision:
    decision_version: str
    outcome: EvidenceOutcome
    reason_code: str
    accepted_source_ids: tuple[str, ...] = ()
    rejected_source_ids: tuple[str, ...] = ()
    score_summary: tuple[tuple[str, float], ...] = ()
    provenance: tuple[EvidenceProvenance, ...] = ()
    trace_id: str = ""

    def __post_init__(self) -> None:
        if not self.decision_version.strip() or not self.reason_code.strip():
            raise ValueError("Decision version and reason are required")
        if not self.trace_id.strip():
            raise ValueError("Decision trace is required")
        if set(self.accepted_source_ids) & set(self.rejected_source_ids):
            raise ValueError("A source cannot be both accepted and rejected")
        if any(not source.strip() for source in (*self.accepted_source_ids, *self.rejected_source_ids)):
            raise ValueError("Source ids must be non-empty")
        if any(score < 0.0 or score > 1.0 for _, score in self.score_summary):
            raise ValueError("Evidence scores must be between 0 and 1")

    def to_canonical_json(self) -> str:
        """Serialize deterministically for benchmark artifacts and audit traces."""
        return dumps(asdict(self), ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


@dataclass(frozen=True)
class ShadowComparison:
    """Sanitized compare-only record; it never affects a user response."""

    case_id: str
    current_state: str
    shadow_outcome: EvidenceOutcome
    disagreement_category: str
    trace_id: str
    provenance_complete: bool

    def __post_init__(self) -> None:
        if not self.case_id.strip() or not self.trace_id.strip():
            raise ValueError("Shadow comparison identity is required")

    def to_canonical_json(self) -> str:
        return dumps(asdict(self), ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def compare_shadow(
    *,
    case_id: str,
    current_state: GroundingState | str,
    decision: EvidenceDecision,
    provenance_complete: bool,
) -> ShadowComparison:
    """Compare old state with a shadow decision without generating prompts."""
    current = str(current_state)
    expected = {
        GroundingState.SUFFICIENT_EVIDENCE.value: EvidenceOutcome.ACCEPT,
        GroundingState.NO_SOURCE.value: EvidenceOutcome.ABSTAIN,
        GroundingState.CONFLICTING_SOURCES.value: EvidenceOutcome.CONFLICT,
    }.get(current)
    if not provenance_complete:
        category = "PROVENANCE_MISMATCH"
    elif expected is decision.outcome:
        category = "AGREEMENT"
    elif current == GroundingState.SUFFICIENT_EVIDENCE.value and decision.outcome is EvidenceOutcome.REJECT:
        category = "CURRENT_ACCEPTS_SHADOW_REJECTS"
    elif current == GroundingState.SUFFICIENT_EVIDENCE.value and decision.outcome is EvidenceOutcome.CONFLICT:
        category = "CURRENT_ACCEPTS_SHADOW_CONFLICT"
    elif current == GroundingState.NO_SOURCE.value and decision.outcome is EvidenceOutcome.RETRIEVAL_FAILURE:
        category = "CURRENT_NO_SOURCE_SHADOW_TECHNICAL"
    else:
        category = "OTHER_DISAGREEMENT"
    return ShadowComparison(
        case_id=case_id,
        current_state=current,
        shadow_outcome=decision.outcome,
        disagreement_category=category,
        trace_id=decision.trace_id,
        provenance_complete=provenance_complete,
    )


def _summary(chunks: Sequence[RetrievedChunk]) -> tuple[tuple[str, float], ...]:
    return tuple((item.chunk.source_id, round(item.score, 6)) for item in chunks)


def decide_evidence(
    chunks: Sequence[RetrievedChunk],
    *,
    decision_version: str = "evidence-v1",
    trace_id: str = "synthetic-trace",
    provenance: Sequence[EvidenceProvenance] = (),
    conflict: bool = False,
    retrieval_failure: bool = False,
    accept: bool = False,
    reason_code: str | None = None,
) -> EvidenceDecision:
    """Create a closed decision from already-produced retrieval evidence.

    ``accept`` is explicit by design: the function never infers validity from
    the mere presence of chunks.  Threshold/calibration policy is selected by
    a later gate and is therefore outside this pure contract.
    """
    source_ids = tuple(dict.fromkeys(item.chunk.source_id for item in chunks))
    if retrieval_failure:
        outcome = EvidenceOutcome.RETRIEVAL_FAILURE
        reason = reason_code or "retrieval_failure"
        accepted, rejected = (), source_ids
    elif conflict:
        outcome = EvidenceOutcome.CONFLICT
        reason = reason_code or "conflicting_evidence"
        accepted, rejected = (), source_ids
    elif not chunks:
        outcome = EvidenceOutcome.ABSTAIN
        reason = reason_code or "no_source"
        accepted, rejected = (), ()
    elif accept:
        outcome = EvidenceOutcome.ACCEPT
        reason = reason_code or "evidence_accepted"
        accepted, rejected = source_ids, ()
    else:
        outcome = EvidenceOutcome.REJECT
        reason = reason_code or "evidence_rejected"
        accepted, rejected = (), source_ids
    return EvidenceDecision(
        decision_version=decision_version,
        outcome=outcome,
        reason_code=reason,
        accepted_source_ids=accepted,
        rejected_source_ids=rejected,
        score_summary=_summary(chunks),
        provenance=tuple(provenance),
        trace_id=trace_id,
    )
