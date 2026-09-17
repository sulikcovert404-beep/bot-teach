"""Immutable final review of staging governance release-readiness evidence."""
from __future__ import annotations

import hashlib
import json
import unicodedata
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from .runtime_admission_bundle import ReferenceStatus, ReferenceToken, _reject_secrets


class ReleaseCertificationOutcome(StrEnum):
 RELEASE_READY_CONFIRMED="RELEASE_READY_CONFIRMED"; RELEASE_READY_CONFIRMED_WITH_WARNINGS="RELEASE_READY_CONFIRMED_WITH_WARNINGS"; RELEASE_NOT_READY="RELEASE_NOT_READY"; RELEASE_BLOCKED="RELEASE_BLOCKED"; UNKNOWN="UNKNOWN"
def _clean(v:Any)->Any:
 if isinstance(v,str): return unicodedata.normalize("NFC",v)
 if isinstance(v,StrEnum): return v.value
 if isinstance(v,dict): return {str(k):_clean(x) for k,x in sorted(v.items(),key=lambda i:str(i[0]))}
 if isinstance(v,(list,tuple,set,frozenset)): return [_clean(x) for x in v]
 return v
@dataclass(frozen=True,slots=True)
class StagingActivationGovernanceReleaseReadinessCertification:
 certification_id:str
 release_readiness_final_review_reference:ReferenceToken
 certification_bundle_reference:ReferenceToken
 final_audit_reference:ReferenceToken
 baseline_freeze_reference:ReferenceToken
 freeze_assurance_reference:ReferenceToken
 activation_control_package_reference:ReferenceToken
 activation_decision_reference:ReferenceToken
 certification_findings:tuple[str,...]=()
 boundary_assertions:dict[str,Any]=field(default_factory=dict)
 trace_reference:ReferenceToken|None=None
 certification_digest:str=field(default="",repr=False)
 def __post_init__(self)->None:
  if not self.certification_id or self.trace_reference is None: raise ValueError("certification_id and trace_reference are required")
  _reject_secrets(self.payload())
  if self.certification_digest and self.certification_digest!=self.compute_digest(): raise ValueError("certification digest mismatch")
  if not self.certification_digest: object.__setattr__(self,"certification_digest",self.compute_digest())
 def payload(self)->dict[str,Any]:
  names=("release_readiness_final_review_reference","certification_bundle_reference","final_audit_reference","baseline_freeze_reference","freeze_assurance_reference","activation_control_package_reference","activation_decision_reference","trace_reference")
  out={"certification_id":self.certification_id,"release_execution":"PROHIBITED","deployment":"PROHIBITED","staging_activation":"PROHIBITED","runtime_activation":"PROHIBITED","runtime_admission":"PROHIBITED","execution":False,"certification_findings":self.certification_findings,"boundary_assertions":self.boundary_assertions}
  for n in names: out[n]=getattr(self,n).to_dict()
  return out
 def canonical_bytes(self)->bytes:return json.dumps(_clean(self.payload()),ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
 def compute_digest(self)->str:return "sha256:"+hashlib.sha256(self.canonical_bytes()).hexdigest()
 def digest_matches(self)->bool:return self.certification_digest==self.compute_digest()
def evaluate_release_certification(r:StagingActivationGovernanceReleaseReadinessCertification)->ReleaseCertificationOutcome:
 refs=[getattr(r,n) for n in ("release_readiness_final_review_reference","certification_bundle_reference","final_audit_reference","baseline_freeze_reference","freeze_assurance_reference","activation_control_package_reference","activation_decision_reference","trace_reference")]
 if not r.digest_matches() or any(x.status is ReferenceStatus.BLOCKED for x in refs): return ReleaseCertificationOutcome.RELEASE_BLOCKED
 if any(x.status is ReferenceStatus.INVALID for x in refs): return ReleaseCertificationOutcome.RELEASE_NOT_READY
 if any(x.status is ReferenceStatus.REQUIRES_REVIEW for x in refs): return ReleaseCertificationOutcome.UNKNOWN
 if r.certification_findings or not r.boundary_assertions or r.boundary_assertions.get("execution") is not False: return ReleaseCertificationOutcome.RELEASE_NOT_READY
 if r.boundary_assertions.get("warnings"): return ReleaseCertificationOutcome.RELEASE_READY_CONFIRMED_WITH_WARNINGS
 return ReleaseCertificationOutcome.RELEASE_READY_CONFIRMED

