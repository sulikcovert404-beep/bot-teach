"""Immutable assurance bundle for pre-activation evidence; never an executor."""
from __future__ import annotations
import hashlib,json,unicodedata
from dataclasses import dataclass,field
from enum import StrEnum
from typing import Any
from .runtime_admission_bundle import ReferenceStatus,ReferenceToken,_reject_secrets
class AssuranceOutcome(StrEnum):
 ASSURANCE_CONFIRMED="ASSURANCE_CONFIRMED"; ASSURANCE_CONFIRMED_WITH_WARNINGS="ASSURANCE_CONFIRMED_WITH_WARNINGS"; ASSURANCE_FAILED="ASSURANCE_FAILED"; ASSURANCE_BLOCKED="ASSURANCE_BLOCKED"; UNKNOWN="UNKNOWN"
def _clean(v:Any)->Any:
 if isinstance(v,str): return unicodedata.normalize("NFC",v)
 if isinstance(v,StrEnum): return v.value
 if isinstance(v,dict): return {str(k):_clean(x) for k,x in sorted(v.items(),key=lambda i:str(i[0]))}
 if isinstance(v,(list,tuple,set,frozenset)): return [_clean(x) for x in v]
 return v
@dataclass(frozen=True,slots=True)
class RuntimeActivationReadinessAssuranceBundle:
 bundle_id:str
 readiness_baseline_freeze_reference:ReferenceToken
 governance_closure_reference:ReferenceToken
 activation_control_plane_reference:ReferenceToken
 activation_decision_reference:ReferenceToken
 evidence_references:tuple[ReferenceToken,...]
 trace_reference:ReferenceToken|None=None
 assurance_findings:tuple[dict[str,Any],...]=()
 assurance_digest:str=field(default="",repr=False)
 def __post_init__(self)->None:
  if not self.bundle_id or not self.evidence_references: raise ValueError("bundle_id and evidence_references are required")
  if self.trace_reference is None: raise ValueError("trace_reference is required")
  _reject_secrets(self.payload())
  if self.assurance_digest and self.assurance_digest!=self.compute_digest(): raise ValueError("assurance digest mismatch")
  if not self.assurance_digest: object.__setattr__(self,"assurance_digest",self.compute_digest())
 def payload(self)->dict[str,Any]:
  out={"bundle_id":self.bundle_id,"evidence_references":[r.to_dict() for r in self.evidence_references],"assurance_findings":list(self.assurance_findings),"runtime_activation":"PROHIBITED","runtime_admission":"PROHIBITED","execution":False}
  for n in ("readiness_baseline_freeze_reference","governance_closure_reference","activation_control_plane_reference","activation_decision_reference","trace_reference"): out[n]=getattr(self,n).to_dict()
  return out
 def canonical_bytes(self)->bytes:return json.dumps(_clean(self.payload()),ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
 def compute_digest(self)->str:return "sha256:"+hashlib.sha256(self.canonical_bytes()).hexdigest()
 def digest_matches(self)->bool:return self.assurance_digest==self.compute_digest()
def evaluate_runtime_activation_readiness_assurance_bundle(b:RuntimeActivationReadinessAssuranceBundle)->AssuranceOutcome:
 refs=[b.readiness_baseline_freeze_reference,b.governance_closure_reference,b.activation_control_plane_reference,b.activation_decision_reference,b.trace_reference,*b.evidence_references]
 if not b.digest_matches() or any(r.status is ReferenceStatus.BLOCKED for r in refs): return AssuranceOutcome.ASSURANCE_BLOCKED
 if any(r.status is ReferenceStatus.INVALID for r in refs): return AssuranceOutcome.ASSURANCE_FAILED
 if any(r.status is ReferenceStatus.REQUIRES_REVIEW for r in refs): return AssuranceOutcome.UNKNOWN
 if any("contradiction" in str(f).lower() for f in b.assurance_findings): return AssuranceOutcome.ASSURANCE_FAILED
 if b.assurance_findings: return AssuranceOutcome.ASSURANCE_CONFIRMED_WITH_WARNINGS
 return AssuranceOutcome.ASSURANCE_CONFIRMED
