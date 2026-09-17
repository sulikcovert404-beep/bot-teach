"""Immutable readiness certification; never grants execution permission."""
from __future__ import annotations

import hashlib
import json
import unicodedata
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from .runtime_admission_bundle import ReferenceStatus, ReferenceToken, _reject_secrets


class CertificationOutcome(StrEnum):
 CERTIFIED_READY="CERTIFIED_READY"; CERTIFIED_READY_WITH_WARNINGS="CERTIFIED_READY_WITH_WARNINGS"; CERTIFICATION_FAILED="CERTIFICATION_FAILED"; CERTIFICATION_BLOCKED="CERTIFICATION_BLOCKED"; UNKNOWN="UNKNOWN"
def _clean(v:Any)->Any:
 if isinstance(v,str): return unicodedata.normalize("NFC",v)
 if isinstance(v,StrEnum): return v.value
 if isinstance(v,dict): return {str(k):_clean(x) for k,x in sorted(v.items(),key=lambda i:str(i[0]))}
 if isinstance(v,(list,tuple,set,frozenset)): return [_clean(x) for x in v]
 return v
@dataclass(frozen=True,slots=True)
class StagingActivationReadinessCertification:
 certification_id:str
 governance_final_audit_reference:ReferenceToken
 governance_master_package_reference:ReferenceToken
 baseline_freeze_reference:ReferenceToken
 freeze_assurance_reference:ReferenceToken
 activation_control_package_reference:ReferenceToken
 activation_decision_reference:ReferenceToken
 certification_findings:tuple[str,...]=()
 certification_scope:dict[str,Any]=field(default_factory=dict)
 boundary_assertions:dict[str,Any]=field(default_factory=dict)
 trace_reference:ReferenceToken|None=None
 certification_digest:str=field(default="",repr=False)
 def __post_init__(self)->None:
  if not self.certification_id: raise ValueError("certification_id is required")
  if self.trace_reference is None: raise ValueError("trace_reference is required")
  _reject_secrets(self.payload())
  if self.certification_digest and self.certification_digest!=self.compute_digest(): raise ValueError("certification digest mismatch")
  if not self.certification_digest: object.__setattr__(self,"certification_digest",self.compute_digest())
 def payload(self)->dict[str,Any]:
  names=("governance_final_audit_reference","governance_master_package_reference","baseline_freeze_reference","freeze_assurance_reference","activation_control_package_reference","activation_decision_reference","trace_reference")
  out={"certification_id":self.certification_id,"certification_findings":self.certification_findings,"certification_scope":self.certification_scope,"boundary_assertions":self.boundary_assertions,"staging_activation":"PROHIBITED","runtime_activation":"PROHIBITED","runtime_admission":"PROHIBITED","execution":False,"deployment":"PROHIBITED"}
  for n in names: out[n]=getattr(self,n).to_dict()
  return out
 def canonical_bytes(self)->bytes:return json.dumps(_clean(self.payload()),ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
 def compute_digest(self)->str:return "sha256:"+hashlib.sha256(self.canonical_bytes()).hexdigest()
 def digest_matches(self)->bool:return self.certification_digest==self.compute_digest()
def evaluate_staging_activation_readiness_certification(c:StagingActivationReadinessCertification)->CertificationOutcome:
 refs=[c.governance_final_audit_reference,c.governance_master_package_reference,c.baseline_freeze_reference,c.freeze_assurance_reference,c.activation_control_package_reference,c.activation_decision_reference,c.trace_reference]
 if not c.digest_matches() or any(r.status is ReferenceStatus.BLOCKED for r in refs): return CertificationOutcome.CERTIFICATION_BLOCKED
 if any(r.status is ReferenceStatus.INVALID for r in refs): return CertificationOutcome.CERTIFICATION_FAILED
 if any(r.status is ReferenceStatus.REQUIRES_REVIEW for r in refs): return CertificationOutcome.UNKNOWN
 if c.certification_findings or not c.certification_scope or not c.boundary_assertions or c.boundary_assertions.get("execution") is not False: return CertificationOutcome.CERTIFICATION_FAILED
 if c.certification_scope.get("warnings"): return CertificationOutcome.CERTIFIED_READY_WITH_WARNINGS
 return CertificationOutcome.CERTIFIED_READY
