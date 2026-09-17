"""Immutable aggregate of staging activation governance artifacts."""
from __future__ import annotations

import hashlib
import json
import unicodedata
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from .runtime_admission_bundle import ReferenceStatus, ReferenceToken, _reject_secrets


class MasterPackageOutcome(StrEnum):
 MASTER_READY="MASTER_READY"; MASTER_READY_WITH_WARNINGS="MASTER_READY_WITH_WARNINGS"; MASTER_NOT_READY="MASTER_NOT_READY"; MASTER_BLOCKED="MASTER_BLOCKED"; UNKNOWN="UNKNOWN"
def _clean(v:Any)->Any:
 if isinstance(v,str): return unicodedata.normalize("NFC",v)
 if isinstance(v,StrEnum): return v.value
 if isinstance(v,dict): return {str(k):_clean(x) for k,x in sorted(v.items(),key=lambda i:str(i[0]))}
 if isinstance(v,(list,tuple,set,frozenset)): return [_clean(x) for x in v]
 return v
@dataclass(frozen=True,slots=True)
class StagingActivationGovernanceMasterPackage:
 package_id:str
 staging_governance_closure_reference:ReferenceToken
 staging_control_package_reference:ReferenceToken
 baseline_freeze_reference:ReferenceToken
 baseline_freeze_assurance_reference:ReferenceToken
 staging_entry_review_reference:ReferenceToken
 validation_assurance_reference:ReferenceToken
 activation_decision_reference:ReferenceToken
 activation_control_plane_reference:ReferenceToken
 master_findings:tuple[str,...]=()
 boundary_assertions:dict[str,Any]=field(default_factory=dict)
 trace_reference:ReferenceToken|None=None
 package_digest:str=field(default="",repr=False)
 def __post_init__(self)->None:
  if not self.package_id: raise ValueError("package_id is required")
  if self.trace_reference is None: raise ValueError("trace_reference is required")
  _reject_secrets(self.payload())
  if self.package_digest and self.package_digest!=self.compute_digest(): raise ValueError("package digest mismatch")
  if not self.package_digest: object.__setattr__(self,"package_digest",self.compute_digest())
 def payload(self)->dict[str,Any]:
  names=("staging_governance_closure_reference","staging_control_package_reference","baseline_freeze_reference","baseline_freeze_assurance_reference","staging_entry_review_reference","validation_assurance_reference","activation_decision_reference","activation_control_plane_reference","trace_reference")
  out={"package_id":self.package_id,"master_findings":self.master_findings,"boundary_assertions":self.boundary_assertions,"staging_activation":"PROHIBITED","runtime_activation":"PROHIBITED","runtime_admission":"PROHIBITED","execution":False,"deployment":"PROHIBITED"}
  for n in names: out[n]=getattr(self,n).to_dict()
  return out
 def canonical_bytes(self)->bytes:return json.dumps(_clean(self.payload()),ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
 def compute_digest(self)->str:return "sha256:"+hashlib.sha256(self.canonical_bytes()).hexdigest()
 def digest_matches(self)->bool:return self.package_digest==self.compute_digest()
def evaluate_staging_activation_governance_master_package(p:StagingActivationGovernanceMasterPackage)->MasterPackageOutcome:
 refs=[p.staging_governance_closure_reference,p.staging_control_package_reference,p.baseline_freeze_reference,p.baseline_freeze_assurance_reference,p.staging_entry_review_reference,p.validation_assurance_reference,p.activation_decision_reference,p.activation_control_plane_reference,p.trace_reference]
 if not p.digest_matches() or any(r.status is ReferenceStatus.BLOCKED for r in refs): return MasterPackageOutcome.MASTER_BLOCKED
 if any(r.status is ReferenceStatus.INVALID for r in refs): return MasterPackageOutcome.MASTER_NOT_READY
 if any(r.status is ReferenceStatus.REQUIRES_REVIEW for r in refs): return MasterPackageOutcome.UNKNOWN
 if p.master_findings or not p.boundary_assertions or p.boundary_assertions.get("execution") is not False: return MasterPackageOutcome.MASTER_NOT_READY
 return MasterPackageOutcome.MASTER_READY
