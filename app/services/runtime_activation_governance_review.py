"""Pure immutable governance review before a future activation review."""
from __future__ import annotations

import hashlib
import json
import unicodedata
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from .runtime_admission_bundle import ReferenceStatus, ReferenceToken, _reject_secrets


class ActivationGovernanceOutcome(StrEnum):
 APPROVED_FOR_ACTIVATION_REVIEW="APPROVED_FOR_ACTIVATION_REVIEW"
 APPROVED_WITH_WARNINGS="APPROVED_WITH_WARNINGS"
 NOT_APPROVED="NOT_APPROVED"
 BLOCKED="BLOCKED"
 UNKNOWN="UNKNOWN"
def _clean(v:Any)->Any:
 if isinstance(v,str): return unicodedata.normalize("NFC",v)
 if isinstance(v,StrEnum): return v.value
 if isinstance(v,dict): return {str(k):_clean(x) for k,x in sorted(v.items(),key=lambda i:str(i[0]))}
 if isinstance(v,(list,tuple,set,frozenset)): return [_clean(x) for x in v]
 return v
@dataclass(frozen=True,slots=True)
class RuntimeActivationGovernanceReview:
 review_id:str
 activation_readiness_package_reference:ReferenceToken
 runtime_entry_decision_reference:ReferenceToken
 governance_freeze_reference:ReferenceToken
 baseline_manifest_reference:ReferenceToken
 change_control_reference:ReferenceToken
 consistency_audit_reference:ReferenceToken
 review_findings:tuple[dict[str,Any],...]=()
 trace_reference:ReferenceToken|None=None
 review_digest:str=field(default="",repr=False)
 def __post_init__(self)->None:
  if not self.review_id: raise ValueError("review_id is required")
  if self.trace_reference is None: raise ValueError("trace_reference is required")
  _reject_secrets(self.payload())
  if self.review_digest and self.review_digest!=self.compute_digest(): raise ValueError("review digest mismatch")
  if not self.review_digest: object.__setattr__(self,"review_digest",self.compute_digest())
 def payload(self)->dict[str,Any]:
  names=("activation_readiness_package_reference","runtime_entry_decision_reference","governance_freeze_reference","baseline_manifest_reference","change_control_reference","consistency_audit_reference","trace_reference")
  out={"review_id":self.review_id,"review_findings":list(self.review_findings),"runtime_activation":"PROHIBITED","runtime_admission":"PROHIBITED","executable":False}
  for n in names: out[n]=getattr(self,n).to_dict()
  return out
 def canonical_bytes(self)->bytes: return json.dumps(_clean(self.payload()),ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
 def compute_digest(self)->str: return "sha256:"+hashlib.sha256(self.canonical_bytes()).hexdigest()
 def digest_matches(self)->bool: return self.review_digest==self.compute_digest()
def evaluate_runtime_activation_governance_review(r:RuntimeActivationGovernanceReview)->ActivationGovernanceOutcome:
 refs=[r.activation_readiness_package_reference,r.runtime_entry_decision_reference,r.governance_freeze_reference,r.baseline_manifest_reference,r.change_control_reference,r.consistency_audit_reference,r.trace_reference]
 if not r.digest_matches() or any(x.status is ReferenceStatus.BLOCKED for x in refs): return ActivationGovernanceOutcome.BLOCKED
 if any(x.status is ReferenceStatus.INVALID for x in refs): return ActivationGovernanceOutcome.NOT_APPROVED
 if any(x.status is ReferenceStatus.REQUIRES_REVIEW for x in refs): return ActivationGovernanceOutcome.UNKNOWN
 if r.review_findings: return ActivationGovernanceOutcome.APPROVED_WITH_WARNINGS
 return ActivationGovernanceOutcome.APPROVED_FOR_ACTIVATION_REVIEW
