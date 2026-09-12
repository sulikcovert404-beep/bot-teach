"""Immutable assurance record for the staging activation baseline freeze."""
from __future__ import annotations
import hashlib,json,unicodedata
from dataclasses import dataclass,field
from enum import StrEnum
from typing import Any
from .runtime_admission_bundle import ReferenceStatus,ReferenceToken,_reject_secrets
class FreezeAssuranceOutcome(StrEnum):
 FREEZE_ASSURANCE_CONFIRMED="FREEZE_ASSURANCE_CONFIRMED"; FREEZE_ASSURANCE_CONFIRMED_WITH_WARNINGS="FREEZE_ASSURANCE_CONFIRMED_WITH_WARNINGS"; FREEZE_ASSURANCE_FAILED="FREEZE_ASSURANCE_FAILED"; FREEZE_ASSURANCE_BLOCKED="FREEZE_ASSURANCE_BLOCKED"; UNKNOWN="UNKNOWN"
def _clean(v:Any)->Any:
 if isinstance(v,str): return unicodedata.normalize("NFC",v)
 if isinstance(v,StrEnum): return v.value
 if isinstance(v,dict): return {str(k):_clean(x) for k,x in sorted(v.items(),key=lambda i:str(i[0]))}
 if isinstance(v,(list,tuple,set,frozenset)): return [_clean(x) for x in v]
 return v
@dataclass(frozen=True,slots=True)
class StagingActivationBaselineFreezeAssurance:
 assurance_id:str
 baseline_freeze_reference:ReferenceToken
 governance_closure_reference:ReferenceToken
 control_package_reference:ReferenceToken
 activation_decision_reference:ReferenceToken
 activation_control_plane_reference:ReferenceToken
 drift_findings:tuple[str,...]=()
 integrity_findings:tuple[str,...]=()
 boundary_assertions:dict[str,Any]=field(default_factory=dict)
 trace_reference:ReferenceToken|None=None
 assurance_digest:str=field(default="",repr=False)
 def __post_init__(self)->None:
  if not self.assurance_id: raise ValueError("assurance_id is required")
  if self.trace_reference is None: raise ValueError("trace_reference is required")
  _reject_secrets(self.payload())
  if self.assurance_digest and self.assurance_digest!=self.compute_digest(): raise ValueError("assurance digest mismatch")
  if not self.assurance_digest: object.__setattr__(self,"assurance_digest",self.compute_digest())
 def payload(self)->dict[str,Any]:
  names=("baseline_freeze_reference","governance_closure_reference","control_package_reference","activation_decision_reference","activation_control_plane_reference","trace_reference")
  out={"assurance_id":self.assurance_id,"drift_findings":self.drift_findings,"integrity_findings":self.integrity_findings,"boundary_assertions":self.boundary_assertions,"staging_activation":"PROHIBITED","runtime_activation":"PROHIBITED","runtime_admission":"PROHIBITED","execution":False,"deployment":"PROHIBITED"}
  for n in names: out[n]=getattr(self,n).to_dict()
  return out
 def canonical_bytes(self)->bytes:return json.dumps(_clean(self.payload()),ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
 def compute_digest(self)->str:return "sha256:"+hashlib.sha256(self.canonical_bytes()).hexdigest()
 def digest_matches(self)->bool:return self.assurance_digest==self.compute_digest()
def evaluate_staging_activation_baseline_freeze_assurance(a:StagingActivationBaselineFreezeAssurance)->FreezeAssuranceOutcome:
 refs=[a.baseline_freeze_reference,a.governance_closure_reference,a.control_package_reference,a.activation_decision_reference,a.activation_control_plane_reference,a.trace_reference]
 if not a.digest_matches() or any(r.status is ReferenceStatus.BLOCKED for r in refs): return FreezeAssuranceOutcome.FREEZE_ASSURANCE_BLOCKED
 if any(r.status is ReferenceStatus.INVALID for r in refs): return FreezeAssuranceOutcome.FREEZE_ASSURANCE_FAILED
 if any(r.status is ReferenceStatus.REQUIRES_REVIEW for r in refs): return FreezeAssuranceOutcome.UNKNOWN
 if a.drift_findings or a.integrity_findings or not a.boundary_assertions: return FreezeAssuranceOutcome.FREEZE_ASSURANCE_FAILED
 if a.boundary_assertions.get("execution") is not False: return FreezeAssuranceOutcome.FREEZE_ASSURANCE_FAILED
 return FreezeAssuranceOutcome.FREEZE_ASSURANCE_CONFIRMED
