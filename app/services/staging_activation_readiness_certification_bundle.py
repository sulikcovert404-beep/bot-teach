"""Immutable packaging bundle for staging readiness certification evidence."""
from __future__ import annotations

import hashlib
import json
import unicodedata
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from .runtime_admission_bundle import ReferenceStatus, ReferenceToken, _reject_secrets


class CertificationBundleOutcome(StrEnum):
 CERTIFICATION_BUNDLE_READY="CERTIFICATION_BUNDLE_READY"; CERTIFICATION_BUNDLE_READY_WITH_WARNINGS="CERTIFICATION_BUNDLE_READY_WITH_WARNINGS"; CERTIFICATION_BUNDLE_NOT_READY="CERTIFICATION_BUNDLE_NOT_READY"; CERTIFICATION_BUNDLE_BLOCKED="CERTIFICATION_BUNDLE_BLOCKED"; UNKNOWN="UNKNOWN"
def _clean(v:Any)->Any:
 if isinstance(v,str): return unicodedata.normalize("NFC",v)
 if isinstance(v,StrEnum): return v.value
 if isinstance(v,dict): return {str(k):_clean(x) for k,x in sorted(v.items(),key=lambda i:str(i[0]))}
 if isinstance(v,(list,tuple,set,frozenset)): return [_clean(x) for x in v]
 return v
@dataclass(frozen=True,slots=True)
class StagingActivationReadinessCertificationBundle:
 bundle_id:str
 readiness_certification_reference:ReferenceToken
 governance_final_audit_reference:ReferenceToken
 governance_master_package_reference:ReferenceToken
 staging_activation_control_package_reference:ReferenceToken
 baseline_freeze_reference:ReferenceToken
 freeze_assurance_reference:ReferenceToken
 activation_decision_reference:ReferenceToken
 activation_control_plane_reference:ReferenceToken
 bundle_findings:tuple[str,...]=()
 boundary_assertions:dict[str,Any]=field(default_factory=dict)
 trace_reference:ReferenceToken|None=None
 bundle_digest:str=field(default="",repr=False)
 def __post_init__(self)->None:
  if not self.bundle_id: raise ValueError("bundle_id is required")
  if self.trace_reference is None: raise ValueError("trace_reference is required")
  _reject_secrets(self.payload())
  if self.bundle_digest and self.bundle_digest!=self.compute_digest(): raise ValueError("bundle digest mismatch")
  if not self.bundle_digest: object.__setattr__(self,"bundle_digest",self.compute_digest())
 def payload(self)->dict[str,Any]:
  names=("readiness_certification_reference","governance_final_audit_reference","governance_master_package_reference","staging_activation_control_package_reference","baseline_freeze_reference","freeze_assurance_reference","activation_decision_reference","activation_control_plane_reference","trace_reference")
  out={"bundle_id":self.bundle_id,"bundle_findings":self.bundle_findings,"boundary_assertions":self.boundary_assertions,"staging_activation":"PROHIBITED","runtime_activation":"PROHIBITED","runtime_admission":"PROHIBITED","execution":False,"deployment":"PROHIBITED"}
  for n in names: out[n]=getattr(self,n).to_dict()
  return out
 def canonical_bytes(self)->bytes:return json.dumps(_clean(self.payload()),ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
 def compute_digest(self)->str:return "sha256:"+hashlib.sha256(self.canonical_bytes()).hexdigest()
 def digest_matches(self)->bool:return self.bundle_digest==self.compute_digest()
def evaluate_staging_activation_readiness_certification_bundle(b:StagingActivationReadinessCertificationBundle)->CertificationBundleOutcome:
 refs=[b.readiness_certification_reference,b.governance_final_audit_reference,b.governance_master_package_reference,b.staging_activation_control_package_reference,b.baseline_freeze_reference,b.freeze_assurance_reference,b.activation_decision_reference,b.activation_control_plane_reference,b.trace_reference]
 if not b.digest_matches() or any(r.status is ReferenceStatus.BLOCKED for r in refs): return CertificationBundleOutcome.CERTIFICATION_BUNDLE_BLOCKED
 if any(r.status is ReferenceStatus.INVALID for r in refs): return CertificationBundleOutcome.CERTIFICATION_BUNDLE_NOT_READY
 if any(r.status is ReferenceStatus.REQUIRES_REVIEW for r in refs): return CertificationBundleOutcome.UNKNOWN
 if b.bundle_findings or not b.boundary_assertions or b.boundary_assertions.get("execution") is not False: return CertificationBundleOutcome.CERTIFICATION_BUNDLE_NOT_READY
 if b.boundary_assertions.get("warnings"): return CertificationBundleOutcome.CERTIFICATION_BUNDLE_READY_WITH_WARNINGS
 return CertificationBundleOutcome.CERTIFICATION_BUNDLE_READY
