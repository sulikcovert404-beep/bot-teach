"""Pure final readiness review contract; never grants runtime authority."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
import json
import unicodedata


class FinalReviewOutcome(StrEnum):
    FINAL_READY = "FINAL_READY"
    FINAL_READY_WITH_WARNINGS = "FINAL_READY_WITH_WARNINGS"
    FINAL_NOT_READY = "FINAL_NOT_READY"
    FINAL_BLOCKED = "FINAL_BLOCKED"
    UNKNOWN = "UNKNOWN"


def _clean(value: str) -> str:
    return unicodedata.normalize("NFC", str(value)).strip()


@dataclass(frozen=True, slots=True)
class RuntimeActivationReadinessFinalReview:
    review_id: str
    readiness_assurance_bundle_reference: str
    readiness_baseline_freeze_reference: str
    governance_closure_reference: str
    activation_control_plane_reference: str
    activation_decision_reference: str
    cross_layer_findings: tuple[str, ...]
    boundary_assertions: tuple[str, ...]
    trace_reference: str
    review_digest: str = ""

    def __post_init__(self) -> None:
        for name in ("review_id", "readiness_assurance_bundle_reference", "readiness_baseline_freeze_reference", "governance_closure_reference", "activation_control_plane_reference", "activation_decision_reference", "trace_reference"):
            value = _clean(getattr(self, name))
            if not value or any(x in value.lower() for x in ("api_key", "password", "secret", "bearer ")):
                raise ValueError(f"invalid or secret-bearing {name}")
            object.__setattr__(self, name, value)
        object.__setattr__(self, "cross_layer_findings", tuple(_clean(x) for x in self.cross_layer_findings))
        object.__setattr__(self, "boundary_assertions", tuple(_clean(x) for x in self.boundary_assertions))
        expected = self.canonical_digest()
        if self.review_digest and self.review_digest != expected:
            raise ValueError("review digest mismatch")
        object.__setattr__(self, "review_digest", expected)

    def payload(self) -> dict[str, object]:
        return {"review_id": self.review_id, "readiness_assurance_bundle_reference": self.readiness_assurance_bundle_reference, "readiness_baseline_freeze_reference": self.readiness_baseline_freeze_reference, "governance_closure_reference": self.governance_closure_reference, "activation_control_plane_reference": self.activation_control_plane_reference, "activation_decision_reference": self.activation_decision_reference, "cross_layer_findings": self.cross_layer_findings, "boundary_assertions": self.boundary_assertions, "trace_reference": self.trace_reference, "runtime_activation": "PROHIBITED", "runtime_admission": "PROHIBITED", "execution": False}

    def canonical_digest(self) -> str:
        body = json.dumps(self.payload(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(body.encode("utf-8")).hexdigest()

    @staticmethod
    def evaluate(*, references: tuple[str, ...], findings: tuple[str, ...] = ()) -> FinalReviewOutcome:
        refs = tuple(_clean(x) for x in references)
        if not refs or any(not x for x in refs) or any("BLOCKED" in x.upper() or "DIGEST_MISMATCH" in x.upper() or "TRACE_FAILURE" in x.upper() for x in refs):
            return FinalReviewOutcome.FINAL_BLOCKED
        if any("CONTRADICTION" in x.upper() or "INVALID" in x.upper() for x in refs):
            return FinalReviewOutcome.FINAL_NOT_READY
        if any("UNKNOWN" in x.upper() for x in refs):
            return FinalReviewOutcome.UNKNOWN
        if findings:
            return FinalReviewOutcome.FINAL_READY_WITH_WARNINGS
        return FinalReviewOutcome.FINAL_READY
