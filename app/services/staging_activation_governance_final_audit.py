"""Immutable final audit of the staging activation governance chain."""
from __future__ import annotations
import hashlib,json,unicodedata
from dataclasses import dataclass,field
from enum import StrEnum
from typing import Any
from .runtime_admission_bundle import ReferenceStatus,ReferenceToken,_reject_secrets
class FinalAuditOutcome(StrEnum):
 AUDIT_PASSED="AUDIT_PASSED"; AUDIT_PASSED_WITH_WARNINGS="AUDIT_PASSED_WITH_WARNINGS"; AUDIT_FAILED="AUDIT_FAILED"; AUDIT_BLOCKED="AUDIT_BLOCKED"; UNKNOWN="UNKNOWN"
def _clean(v:Any)->Any:
 if isinstance(v,str): return unicodedata.normalize("NFC",v)
 if isinstance(v,StrEnum): return v.value
 if isinstance(v,dict): return {str(k):_clean(x) for k,x in sorted(v.items(),key=lambda i:str(i[0]))}
 if isinstance(v,(list,tuple,set,frozenset)): return [_clean(x) for x in v]
 return v
@dataclass(frozen=True,slots=True)
class StagingActivationGovernanceFinalAudit:
 audit_id:str
 governance_master_package_reference:ReferenceToken
 staging_activation_control_package_reference:ReferenceToken
 baseline_freeze_reference:ReferenceToken
 baseline_assurance_reference:ReferenceToken
 closure_reference:ReferenceToken
 entry_review_reference:ReferenceToken
 audit_findings:tuple[str,...]=()
 integrity_summary:dict[str,Any]=field(default_factory=dict)
 boundary_assertions:dict[str,Any]=field(default_factory=dict)
 trace_reference:ReferenceToken|None=None
 audit_digest:str=field(default="",repr=False)
 def __post_init__(self)->None:
  if not self.audit_id: raise ValueError("audit_id is required")
  if self.trace_reference is None: raise ValueError("trace_reference is required")
  _reject_secrets(self.payload())
  if self.audit_digest and self.audit_digest!=self.compute_digest(): raise ValueError("audit digest mismatch")
  if not self.audit_digest: object.__setattr__(self,"audit_digest",self.compute_digest())
 def payload(self)->dict[str,Any]:
  names=("governance_master_package_reference","staging_activation_control_package_reference","baseline_freeze_reference","baseline_assurance_reference","closure_reference","entry_review_reference","trace_reference")
  out={"audit_id":self.audit_id,"audit_findings":self.audit_findings,"integrity_summary":self.integrity_summary,"boundary_assertions":self.boundary_assertions,"staging_activation":"PROHIBITED","runtime_activation":"PROHIBITED","runtime_admission":"PROHIBITED","execution":False,"deployment":"PROHIBITED"}
  for n in names: out[n]=getattr(self,n).to_dict()
  return out
 def canonical_bytes(self)->bytes:return json.dumps(_clean(self.payload()),ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
 def compute_digest(self)->str:return "sha256:"+hashlib.sha256(self.canonical_bytes()).hexdigest()
 def digest_matches(self)->bool:return self.audit_digest==self.compute_digest()
def evaluate_staging_activation_governance_final_audit(a:StagingActivationGovernanceFinalAudit)->FinalAuditOutcome:
 refs=[a.governance_master_package_reference,a.staging_activation_control_package_reference,a.baseline_freeze_reference,a.baseline_assurance_reference,a.closure_reference,a.entry_review_reference,a.trace_reference]
 if not a.digest_matches() or any(r.status is ReferenceStatus.BLOCKED for r in refs): return FinalAuditOutcome.AUDIT_BLOCKED
 if any(r.status is ReferenceStatus.INVALID for r in refs): return FinalAuditOutcome.AUDIT_FAILED
 if any(r.status is ReferenceStatus.REQUIRES_REVIEW for r in refs): return FinalAuditOutcome.UNKNOWN
 if a.audit_findings or not a.integrity_summary or not a.boundary_assertions: return FinalAuditOutcome.AUDIT_FAILED
 if a.boundary_assertions.get("execution") is not False: return FinalAuditOutcome.AUDIT_FAILED
 if a.integrity_summary.get("warnings"): return FinalAuditOutcome.AUDIT_PASSED_WITH_WARNINGS
 return FinalAuditOutcome.AUDIT_PASSED
