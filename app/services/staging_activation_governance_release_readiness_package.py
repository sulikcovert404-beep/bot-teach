"""Immutable release-readiness package; packaging only, never release execution."""
from __future__ import annotations
import hashlib,json,unicodedata
from dataclasses import dataclass,field
from enum import StrEnum
from typing import Any
from .runtime_admission_bundle import ReferenceStatus,ReferenceToken,_reject_secrets
class ReleaseReadinessOutcome(StrEnum):
 RELEASE_READY="RELEASE_READY"; RELEASE_READY_WITH_WARNINGS="RELEASE_READY_WITH_WARNINGS"; RELEASE_NOT_READY="RELEASE_NOT_READY"; RELEASE_BLOCKED="RELEASE_BLOCKED"; UNKNOWN="UNKNOWN"
def _clean(v:Any)->Any:
 if isinstance(v,str): return unicodedata.normalize("NFC",v)
 if isinstance(v,StrEnum): return v.value
 if isinstance(v,dict): return {str(k):_clean(x) for k,x in sorted(v.items(),key=lambda i:str(i[0]))}
 if isinstance(v,(list,tuple,set,frozenset)): return [_clean(x) for x in v]
 return v
@dataclass(frozen=True,slots=True)
class StagingActivationGovernanceReleaseReadinessPackage:
 package_id:str
 certification_bundle_reference:ReferenceToken
 readiness_certification_reference:ReferenceToken
 final_audit_reference:ReferenceToken
 governance_master_package_reference:ReferenceToken
 baseline_freeze_reference:ReferenceToken
 freeze_assurance_reference:ReferenceToken
 staging_control_package_reference:ReferenceToken
 activation_decision_reference:ReferenceToken
 activation_control_plane_reference:ReferenceToken
 release_findings:tuple[str,...]=()
 boundary_assertions:dict[str,Any]=field(default_factory=dict)
 trace_reference:ReferenceToken|None=None
 package_digest:str=field(default="",repr=False)
 def __post_init__(self)->None:
  if not self.package_id or self.trace_reference is None: raise ValueError("package_id and trace_reference are required")
  _reject_secrets(self.payload())
  if self.package_digest and self.package_digest!=self.compute_digest(): raise ValueError("package digest mismatch")
  if not self.package_digest: object.__setattr__(self,"package_digest",self.compute_digest())
 def payload(self)->dict[str,Any]:
  names=("certification_bundle_reference","readiness_certification_reference","final_audit_reference","governance_master_package_reference","baseline_freeze_reference","freeze_assurance_reference","staging_control_package_reference","activation_decision_reference","activation_control_plane_reference","trace_reference")
  out={"package_id":self.package_id,"release":"REVIEW_ONLY","staging_activation":"PROHIBITED","runtime_activation":"PROHIBITED","runtime_admission":"PROHIBITED","execution":False,"deployment":"PROHIBITED","release_findings":self.release_findings,"boundary_assertions":self.boundary_assertions}
  for n in names: out[n]=getattr(self,n).to_dict()
  return out
 def canonical_bytes(self)->bytes: return json.dumps(_clean(self.payload()),ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
 def compute_digest(self)->str: return "sha256:"+hashlib.sha256(self.canonical_bytes()).hexdigest()
 def digest_matches(self)->bool: return self.package_digest==self.compute_digest()
def evaluate_release_readiness_package(p:StagingActivationGovernanceReleaseReadinessPackage)->ReleaseReadinessOutcome:
 refs=[getattr(p,n) for n in ("certification_bundle_reference","readiness_certification_reference","final_audit_reference","governance_master_package_reference","baseline_freeze_reference","freeze_assurance_reference","staging_control_package_reference","activation_decision_reference","activation_control_plane_reference","trace_reference")]
 if not p.digest_matches() or any(r.status is ReferenceStatus.BLOCKED for r in refs): return ReleaseReadinessOutcome.RELEASE_BLOCKED
 if any(r.status is ReferenceStatus.INVALID for r in refs): return ReleaseReadinessOutcome.RELEASE_NOT_READY
 if any(r.status is ReferenceStatus.REQUIRES_REVIEW for r in refs): return ReleaseReadinessOutcome.UNKNOWN
 if p.release_findings or not p.boundary_assertions or p.boundary_assertions.get("execution") is not False: return ReleaseReadinessOutcome.RELEASE_NOT_READY
 if p.boundary_assertions.get("warnings"): return ReleaseReadinessOutcome.RELEASE_READY_WITH_WARNINGS
 return ReleaseReadinessOutcome.RELEASE_READY
