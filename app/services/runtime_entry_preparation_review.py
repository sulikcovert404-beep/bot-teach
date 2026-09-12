"""Pure immutable, non-authoritative runtime-entry preparation review contract."""
from __future__ import annotations
import hashlib, json, re, unicodedata
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from .runtime_admission_bundle import ReferenceStatus, ReferenceToken

class PreparationOutcome(StrEnum):
    READY_FOR_PREPARATION = "READY_FOR_PREPARATION"
    READY_WITH_WARNINGS = "READY_WITH_WARNINGS"
    NOT_READY = "NOT_READY"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"

_SECRET = re.compile(r"(?i)(api[_-]?key|token|password|secret|credential|authorization|private[_-]?key)")
def _clean(v: Any) -> Any:
    if isinstance(v, str): return unicodedata.normalize("NFC", v)
    if isinstance(v, StrEnum): return v.value
    if isinstance(v, dict): return {str(k): _clean(x) for k,x in sorted(v.items(), key=lambda i: str(i[0]))}
    if isinstance(v, (tuple,list,set,frozenset)): return [_clean(x) for x in v]
    return v
def _reject(v: Any) -> None:
    if isinstance(v,str) and _SECRET.search(v): raise ValueError("secret-like content is not permitted")
    if isinstance(v,dict):
        for k,x in v.items():
            if _SECRET.search(str(k)): raise ValueError("secret-like field is not permitted")
            _reject(x)
    elif isinstance(v,(tuple,list,set,frozenset)):
        for x in v: _reject(x)

@dataclass(frozen=True, slots=True)
class RuntimeEntryPreparationReview:
    review_id: str
    freeze_reference: ReferenceToken
    baseline_reference: ReferenceToken
    closure_reference: ReferenceToken
    handoff_reference: ReferenceToken
    consistency_reference: ReferenceToken
    readiness_reference: ReferenceToken
    preparation_findings: tuple[str, ...]
    trace_reference: ReferenceToken
    review_digest: str = field(default="", repr=False)
    def __post_init__(self) -> None:
        if not self.review_id: raise ValueError("review_id is required")
        _reject(self.payload())
        if self.review_digest and self.review_digest != self.compute_digest(): raise ValueError("review digest mismatch")
        if not self.review_digest: object.__setattr__(self, "review_digest", self.compute_digest())
    def payload(self) -> dict[str,Any]:
        return {"review_id":self.review_id,"freeze_reference":self.freeze_reference.to_dict(),"baseline_reference":self.baseline_reference.to_dict(),"closure_reference":self.closure_reference.to_dict(),"handoff_reference":self.handoff_reference.to_dict(),"consistency_reference":self.consistency_reference.to_dict(),"readiness_reference":self.readiness_reference.to_dict(),"preparation_findings":list(self.preparation_findings),"trace_reference":self.trace_reference.to_dict()}
    def canonical_bytes(self)->bytes: return json.dumps(_clean(self.payload()),ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
    def compute_digest(self)->str: return "sha256:"+hashlib.sha256(self.canonical_bytes()).hexdigest()
    def digest_matches(self)->bool: return self.review_digest==self.compute_digest()

def evaluate_runtime_entry_preparation(review: RuntimeEntryPreparationReview)->PreparationOutcome:
    refs=(review.freeze_reference,review.baseline_reference,review.closure_reference,review.handoff_reference,review.consistency_reference,review.readiness_reference,review.trace_reference)
    if not review.digest_matches(): return PreparationOutcome.BLOCKED
    if any(r.status is ReferenceStatus.BLOCKED for r in refs): return PreparationOutcome.BLOCKED
    if any(r.status is ReferenceStatus.INVALID for r in refs): return PreparationOutcome.NOT_READY
    if any(r.status is ReferenceStatus.REQUIRES_REVIEW for r in refs): return PreparationOutcome.UNKNOWN
    if review.preparation_findings: return PreparationOutcome.READY_WITH_WARNINGS
    return PreparationOutcome.READY_FOR_PREPARATION
