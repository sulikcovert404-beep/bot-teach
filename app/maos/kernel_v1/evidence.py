"""Append-only logical evidence values and pure history append operation."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from app.maos.kernel_v1.models import RiskClass


@dataclass(frozen=True, slots=True)
class EvidenceEntry:
    evidence_id: str
    task_id: str
    trace_id: str
    producer_id: str
    producer_principal_id: str
    logical_role: str
    provider_ref: str | None
    source_type: str
    source_locator_ref: str
    content_hash: str
    captured_at: datetime
    observed_at: datetime
    method: str
    schema_version: str
    limitations: tuple[str, ...]
    freshness_ref: str | None
    tenant_id: str | None
    artifact_ref: str | None
    redaction_status: str
    supersedes_evidence_id: str | None = None

    def __post_init__(self) -> None:
        if not all((self.evidence_id, self.task_id, self.trace_id, self.producer_id, self.producer_principal_id, self.logical_role, self.source_type, self.source_locator_ref, self.content_hash, self.method, self.schema_version, self.redaction_status)):
            raise ValueError("evidence identity and provenance fields are required")
        if len(self.content_hash) != 64 or any(ch not in "0123456789abcdef" for ch in self.content_hash.lower()):
            raise ValueError("content_hash must be a SHA-256 hex digest")
        if self.redaction_status not in {"redacted", "non_sensitive"}:
            raise ValueError("evidence must be explicitly redacted or non-sensitive")
        if self.captured_at.tzinfo is None or self.observed_at.tzinfo is None:
            raise ValueError("evidence timestamps must be timezone-aware")
        if not isinstance(self.limitations, tuple):
            raise TypeError("evidence limitations must be immutable")


@dataclass(frozen=True, slots=True)
class EvidenceHistory:
    entries: tuple[EvidenceEntry, ...] = ()


@dataclass(frozen=True, slots=True)
class ArtifactReference:
    artifact_id: str
    task_id: str
    producer_id: str
    content_hash: str
    schema_version: str
    created_at: datetime
    tenant_id: str | None

    def __post_init__(self) -> None:
        if not all((self.artifact_id, self.task_id, self.producer_id, self.schema_version)):
            raise ValueError("artifact metadata references are required")
        if len(self.content_hash) != 64 or any(ch not in "0123456789abcdef" for ch in self.content_hash.lower()):
            raise ValueError("artifact content_hash must be a SHA-256 hex digest")
        if self.created_at.tzinfo is None:
            raise ValueError("artifact timestamp must be timezone-aware")


class ReviewOutcome(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    INCONCLUSIVE = "inconclusive"


@dataclass(frozen=True, slots=True)
class ReviewRecord:
    review_id: str
    task_id: str
    reviewer_principal_id: str
    reviewer_instance_id: str
    author_instance_id: str
    logical_role: str
    outcome: ReviewOutcome
    acceptance_criteria_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    provenance_ref: str
    reviewed_at: datetime
    independence_required: bool = True

    def __post_init__(self) -> None:
        if not all((self.review_id, self.task_id, self.reviewer_principal_id, self.reviewer_instance_id, self.author_instance_id, self.logical_role, self.provenance_ref)):
            raise ValueError("review provenance fields are required")
        if self.independence_required and self.reviewer_instance_id == self.author_instance_id:
            raise ValueError("independent review requires distinct logical instances")
        if self.reviewed_at.tzinfo is None:
            raise ValueError("review timestamp must be timezone-aware")


class DecisionAuthority(StrEnum):
    COMMANDER = "commander"
    POLICY_ENGINE = "policy_engine"


@dataclass(frozen=True, slots=True)
class DecisionRecord:
    decision_id: str
    authority: DecisionAuthority
    task_id: str
    scope_ref: str
    rationale_ref: str
    evidence_refs: tuple[str, ...]
    risk_class: RiskClass
    reversible: bool
    timestamp: datetime
    policy_version: str
    decision_gate_ref: str | None = None

    def __post_init__(self) -> None:
        if not all((self.decision_id, self.task_id, self.scope_ref, self.rationale_ref, self.policy_version)):
            raise ValueError("decision authority, scope, rationale and policy are required")
        if self.timestamp.tzinfo is None:
            raise ValueError("decision timestamp must be timezone-aware")
        if self.risk_class in {RiskClass.HIGH, RiskClass.CRITICAL} and (
            self.authority is not DecisionAuthority.COMMANDER or not self.decision_gate_ref
        ):
            raise ValueError("high-risk decision requires explicit Commander gate evidence")


def append_evidence(history: EvidenceHistory, entry: EvidenceEntry) -> EvidenceHistory:
    """Return a new logical history; duplicate ids or invalid supersession are rejected."""
    if any(existing.evidence_id == entry.evidence_id for existing in history.entries):
        raise ValueError("evidence id already exists; logical history cannot be overwritten")
    if entry.supersedes_evidence_id and not any(
        existing.evidence_id == entry.supersedes_evidence_id for existing in history.entries
    ):
        raise ValueError("superseded evidence must already exist")
    if entry.supersedes_evidence_id and not any(
        existing.evidence_id == entry.supersedes_evidence_id
        and existing.task_id == entry.task_id
        and existing.tenant_id == entry.tenant_id
        for existing in history.entries
    ):
        raise ValueError("supersession cannot cross task or tenant boundaries")
    return EvidenceHistory((*history.entries, entry))
