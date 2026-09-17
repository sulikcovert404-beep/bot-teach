"""Pure change-control contract applied after a baseline is frozen."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from .runtime_admission_bundle import ReferenceStatus, ReferenceToken


class ChangeOutcome(StrEnum):
    ALLOWED = "ALLOWED"
    ALLOWED_WITH_REVIEW = "ALLOWED_WITH_REVIEW"
    REJECTED = "REJECTED"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


_SECRET = re.compile(r"(?i)(api[_-]?key|token|password|secret|credential|authorization|private[_-]?key)")


def _clean(value: Any) -> Any:
    if isinstance(value, str): return unicodedata.normalize("NFC", value)
    if isinstance(value, StrEnum): return value.value
    if isinstance(value, dict): return {str(k): _clean(v) for k, v in sorted(value.items(), key=lambda x: str(x[0]))}
    if isinstance(value, (tuple, list, set, frozenset)):
        return sorted((_clean(v) for v in value), key=lambda v: json.dumps(v, ensure_ascii=False, sort_keys=True))
    return value


def _reject(value: Any) -> None:
    if isinstance(value, str) and _SECRET.search(value): raise ValueError("secret-like content is not permitted")
    if isinstance(value, dict):
        for k, v in value.items():
            if _SECRET.search(str(k)): raise ValueError("secret-like field is not permitted")
            _reject(v)
    elif isinstance(value, (tuple, list, set, frozenset)):
        for v in value: _reject(v)


def _canonical(value: Any) -> bytes:
    return json.dumps(_clean(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


@dataclass(frozen=True, slots=True)
class BaselineChangeControl:
    change_request_id: str
    baseline_reference: ReferenceToken
    proposed_changes: tuple[str, ...]
    impact_reference: ReferenceToken | None
    version_transition_reference: ReferenceToken | None
    trace_reference: ReferenceToken
    decision_digest: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        if not self.change_request_id or not self.baseline_reference or not self.trace_reference:
            raise ValueError("change identity and references are required")
        object.__setattr__(self, "proposed_changes", tuple(sorted(set(unicodedata.normalize("NFC", x) for x in self.proposed_changes))))
        _reject(self.payload())
        if self.decision_digest and self.decision_digest != self.compute_digest(): raise ValueError("decision digest mismatch")
        if not self.decision_digest: object.__setattr__(self, "decision_digest", self.compute_digest())

    def payload(self) -> dict[str, Any]:
        return {"change_request_id": self.change_request_id, "baseline_reference": self.baseline_reference.to_dict(),
                "proposed_changes": self.proposed_changes, "impact_reference": self.impact_reference.to_dict() if self.impact_reference else None,
                "version_transition_reference": self.version_transition_reference.to_dict() if self.version_transition_reference else None,
                "trace_reference": self.trace_reference.to_dict()}

    def canonical_bytes(self) -> bytes: return _canonical(self.payload())
    def compute_digest(self) -> str: return "sha256:" + hashlib.sha256(self.canonical_bytes()).hexdigest()
    def digest_matches(self) -> bool: return self.decision_digest == self.compute_digest()


def evaluate_change_control(control: BaselineChangeControl, *, baseline_frozen: bool = True) -> ChangeOutcome:
    if not control.digest_matches(): return ChangeOutcome.REJECTED
    if control.baseline_reference.status is not ReferenceStatus.VALID or not baseline_frozen: return ChangeOutcome.BLOCKED
    if control.trace_reference.status is ReferenceStatus.REQUIRES_REVIEW: return ChangeOutcome.UNKNOWN
    if control.trace_reference.status is not ReferenceStatus.VALID: return ChangeOutcome.BLOCKED
    if control.impact_reference is None and control.proposed_changes: return ChangeOutcome.BLOCKED
    if control.impact_reference is not None and control.impact_reference.status is not ReferenceStatus.VALID: return ChangeOutcome.BLOCKED
    if control.version_transition_reference is None and control.proposed_changes: return ChangeOutcome.BLOCKED
    if control.version_transition_reference is not None:
        if control.version_transition_reference.status is not ReferenceStatus.VALID: return ChangeOutcome.REJECTED
        if "INCOMPATIBLE" in control.version_transition_reference.reference_id.upper(): return ChangeOutcome.REJECTED
        if "REVIEW" in control.version_transition_reference.reference_id.upper(): return ChangeOutcome.ALLOWED_WITH_REVIEW
    return ChangeOutcome.ALLOWED
