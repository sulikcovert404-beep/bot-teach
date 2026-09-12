"""Immutable, non-authoritative snapshot of activation readiness."""
from __future__ import annotations
import hashlib,json,unicodedata
from dataclasses import dataclass,field
from enum import StrEnum
from typing import Any
from .runtime_admission_bundle import ReferenceStatus,ReferenceToken,_reject_secrets
class BaselineFreezeOutcome(StrEnum):
 BASELINE_FROZEN="BASELINE_FROZEN"; BASELINE_FROZEN_WITH_WARNINGS="BASELINE_FROZEN_WITH_WARNINGS"; BASELINE_NOT_FROZEN="BASELINE_NOT_FROZEN"; BASELINE_BLOCKED="BASELINE_BLOCKED"; UNKNOWN="UNKNOWN"
def _clean(v:Any)->Any:
 if isinstance(v,str): return unicodedata.normalize("NFC",v)
 if isinstance(v,StrEnum): return v.value
 if isinstance(v,dict): return {str(k):_clean(x) for k,x in sorted(v.items(),key=lambda i:str(i[0]))}
 if isinstance(v,(list,tuple,set,frozenset)): return [_clean(x) for x in v]
 return v
@dataclass(frozen=True,slots=True)
class RuntimeActivationReadinessBaselineFreeze:
 freeze_id:str
 governance_closure_reference:ReferenceToken
 activation_control_plane_reference:ReferenceToken
 activation_decision_reference:ReferenceToken
 readiness_package_reference:ReferenceToken
 entry_preparation_reference:ReferenceToken
 baseline_reference:ReferenceToken
 change_control_reference:ReferenceToken
 captured_state:dict[str,Any]=field(default_factory=dict)
 trace_reference:ReferenceToken|None=None
 freeze_digest:str=field(default="",repr=False)
 def __post_init__(self)->None:
  if not self.freeze_id: raise ValueError("freeze_id is required")
  if self.trace_reference is None: raise ValueError("trace_reference is required")
  _reject_secrets(self.payload())
  if self.freeze_digest and self.freeze_digest!=self.compute_digest(): raise ValueError("freeze digest mismatch")
  if not self.freeze_digest: object.__setattr__(self,"freeze_digest",self.compute_digest())
 def payload(self)->dict[str,Any]:
  names=("governance_closure_reference","activation_control_plane_reference","activation_decision_reference","readiness_package_reference","entry_preparation_reference","baseline_reference","change_control_reference","trace_reference")
  out={"freeze_id":self.freeze_id,"captured_state":self.captured_state,"runtime_activation":"PROHIBITED","runtime_admission":"PROHIBITED","execution":False}
  for n in names: out[n]=getattr(self,n).to_dict()
  return out
 def canonical_bytes(self)->bytes:return json.dumps(_clean(self.payload()),ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
 def compute_digest(self)->str:return "sha256:"+hashlib.sha256(self.canonical_bytes()).hexdigest()
 def digest_matches(self)->bool:return self.freeze_digest==self.compute_digest()
def evaluate_runtime_activation_readiness_baseline_freeze(f:RuntimeActivationReadinessBaselineFreeze)->BaselineFreezeOutcome:
 refs=[f.governance_closure_reference,f.activation_control_plane_reference,f.activation_decision_reference,f.readiness_package_reference,f.entry_preparation_reference,f.baseline_reference,f.change_control_reference,f.trace_reference]
 if not f.digest_matches() or any(r.status is ReferenceStatus.BLOCKED for r in refs): return BaselineFreezeOutcome.BASELINE_BLOCKED
 if any(r.status is ReferenceStatus.INVALID for r in refs): return BaselineFreezeOutcome.BASELINE_NOT_FROZEN
 if any(r.status is ReferenceStatus.REQUIRES_REVIEW for r in refs): return BaselineFreezeOutcome.UNKNOWN
 if not f.captured_state: return BaselineFreezeOutcome.BASELINE_NOT_FROZEN
 if f.captured_state.get("warnings"): return BaselineFreezeOutcome.BASELINE_FROZEN_WITH_WARNINGS
 return BaselineFreezeOutcome.BASELINE_FROZEN
