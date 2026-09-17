"""Pure immutable handoff contract between governance and future readiness."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from .runtime_admission_bundle import ReferenceStatus, ReferenceToken


class HandoffOutcome(StrEnum):
    ACCEPTED = "ACCEPTED"
    ACCEPTED_WITH_WARNINGS = "ACCEPTED_WITH_WARNINGS"
    REJECTED = "REJECTED"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"

_SECRET = re.compile(r"(?i)(api[_-]?key|token|password|secret|credential|authorization|private[_-]?key)")

def _clean(v: Any) -> Any:
    if isinstance(v, str): return unicodedata.normalize("NFC", v)
    if isinstance(v, StrEnum): return v.value
    if isinstance(v, dict): return {str(k): _clean(x) for k, x in sorted(v.items(), key=lambda x: str(x[0]))}
    if isinstance(v, (tuple, list, set, frozenset)): return [_clean(x) for x in v]
    return v

def _reject(v: Any) -> None:
    if isinstance(v, str) and _SECRET.search(v): raise ValueError("secret-like content is not permitted")
    if isinstance(v, dict):
        for k, x in v.items():
            if _SECRET.search(str(k)): raise ValueError("secret-like field is not permitted")
            _reject(x)
    elif isinstance(v, (tuple, list, set, frozenset)):
        for x in v: _reject(x)

@dataclass(frozen=True, slots=True)
class GovernanceHandoffBundle:
    handoff_id: str
    baseline_reference: ReferenceToken
    closure_reference: ReferenceToken
    readiness_snapshot_reference: ReferenceToken
    change_control_reference: ReferenceToken
    evidence_references: tuple[ReferenceToken, ...]
    trace_reference: ReferenceToken
    handoff_digest: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        if not self.handoff_id: raise ValueError("handoff_id is required")
        if not self.evidence_references: raise ValueError("evidence_references are required")
        _reject(self.payload())
        if self.handoff_digest and self.handoff_digest != self.compute_digest(): raise ValueError("handoff digest mismatch")
        if not self.handoff_digest: object.__setattr__(self, "handoff_digest", self.compute_digest())

    def payload(self) -> dict[str, Any]:
        return {"handoff_id": self.handoff_id, "baseline_reference": self.baseline_reference.to_dict(),
                "closure_reference": self.closure_reference.to_dict(), "readiness_snapshot_reference": self.readiness_snapshot_reference.to_dict(),
                "change_control_reference": self.change_control_reference.to_dict(),
                "evidence_references": [x.to_dict() for x in self.evidence_references], "trace_reference": self.trace_reference.to_dict()}
    def canonical_bytes(self) -> bytes: return json.dumps(_clean(self.payload()), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    def compute_digest(self) -> str: return "sha256:" + hashlib.sha256(self.canonical_bytes()).hexdigest()
    def digest_matches(self) -> bool: return self.handoff_digest == self.compute_digest()

def evaluate_handoff(bundle: GovernanceHandoffBundle, *, baseline_frozen: bool = True) -> HandoffOutcome:
    if not bundle.digest_matches(): return HandoffOutcome.REJECTED
    refs = (bundle.baseline_reference, bundle.closure_reference, bundle.readiness_snapshot_reference, bundle.change_control_reference)
    if not baseline_frozen or bundle.baseline_reference.status is ReferenceStatus.BLOCKED: return HandoffOutcome.BLOCKED
    if any(r.status is ReferenceStatus.INVALID for r in refs) or any(r.status is ReferenceStatus.INVALID for r in bundle.evidence_references): return HandoffOutcome.REJECTED
    if any(r.status is ReferenceStatus.BLOCKED for r in refs) or any(r.status is ReferenceStatus.BLOCKED for r in bundle.evidence_references): return HandoffOutcome.BLOCKED
    if any(r.status is ReferenceStatus.REQUIRES_REVIEW for r in refs + bundle.evidence_references): return HandoffOutcome.UNKNOWN
    if bundle.trace_reference.status is not ReferenceStatus.VALID: return HandoffOutcome.BLOCKED
    return HandoffOutcome.ACCEPTED_WITH_WARNINGS if any(r.reference_id.upper().find("WARN") >= 0 for r in refs) else HandoffOutcome.ACCEPTED
