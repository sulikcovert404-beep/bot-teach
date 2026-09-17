"""Immutable governance sign-off record for release-readiness evidence."""
from __future__ import annotations

import hashlib
import json
import unicodedata
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from .runtime_admission_bundle import ReferenceStatus, ReferenceToken, _reject_secrets


class SignOffOutcome(StrEnum):
 SIGNOFF_ACCEPTED="SIGNOFF_ACCEPTED"; SIGNOFF_ACCEPTED_WITH_WARNINGS="SIGNOFF_ACCEPTED_WITH_WARNINGS"; SIGNOFF_REJECTED="SIGNOFF_REJECTED"; SIGNOFF_BLOCKED="SIGNOFF_BLOCKED"; UNKNOWN="UNKNOWN"
def _clean(v:Any)->Any:
 if isinstance(v,str): return unicodedata.normalize("NFC",v)
 if isinstance(v,StrEnum): return v.value
 if isinstance(v,dict): return {str(k):_clean(x) for k,x in sorted(v.items(),key=lambda i:str(i[0]))}
 if isinstance(v,(list,tuple,set,frozenset)): return [_clean(x) for x in v]
 return v
@dataclass(frozen=True,slots=True)
class StagingActivationGovernanceReleaseReadinessSignOffRecord:
 signoff_id:str
 final_governance_package_reference:ReferenceToken
 master_assurance_reference:ReferenceToken
 release_certification_reference:ReferenceToken
 final_audit_reference:ReferenceToken
 signoff_scope:tuple[str,...]=()
 signoff_findings:tuple[str,...]=()
 boundary_assertions:dict[str,Any]=field(default_factory=dict)
 trace_reference:ReferenceToken|None=None
 signoff_digest:str=field(default="",repr=False)
 def __post_init__(self)->None:
  if not self.signoff_id or self.trace_reference is None: raise ValueError("signoff_id and trace_reference are required")
  _reject_secrets(self.payload())
  if self.signoff_digest and self.signoff_digest!=self.compute_digest(): raise ValueError("signoff digest mismatch")
  if not self.signoff_digest: object.__setattr__(self,"signoff_digest",self.compute_digest())
 def payload(self)->dict[str,Any]:
  names=("final_governance_package_reference","master_assurance_reference","release_certification_reference","final_audit_reference","trace_reference")
  out={"signoff_id":self.signoff_id,"release_execution":"PROHIBITED","deployment":"PROHIBITED","staging_activation":"PROHIBITED","runtime_activation":"PROHIBITED","runtime_admission":"PROHIBITED","execution":False,"signoff_scope":self.signoff_scope,"signoff_findings":self.signoff_findings,"boundary_assertions":self.boundary_assertions}
  for n in names: out[n]=getattr(self,n).to_dict()
  return out
 def canonical_bytes(self)->bytes:return json.dumps(_clean(self.payload()),ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
 def compute_digest(self)->str:return "sha256:"+hashlib.sha256(self.canonical_bytes()).hexdigest()
 def digest_matches(self)->bool:return self.signoff_digest==self.compute_digest()
def evaluate_signoff(r:StagingActivationGovernanceReleaseReadinessSignOffRecord)->SignOffOutcome:
 refs=[getattr(r,n) for n in ("final_governance_package_reference","master_assurance_reference","release_certification_reference","final_audit_reference","trace_reference")]
 if not r.digest_matches() or any(x.status is ReferenceStatus.BLOCKED for x in refs): return SignOffOutcome.SIGNOFF_BLOCKED
 if any(x.status is ReferenceStatus.INVALID for x in refs): return SignOffOutcome.SIGNOFF_REJECTED
 if any(x.status is ReferenceStatus.REQUIRES_REVIEW for x in refs): return SignOffOutcome.UNKNOWN
 if r.signoff_findings or r.boundary_assertions.get("execution") is not False: return SignOffOutcome.SIGNOFF_REJECTED
 if r.boundary_assertions.get("warnings"): return SignOffOutcome.SIGNOFF_ACCEPTED_WITH_WARNINGS
 return SignOffOutcome.SIGNOFF_ACCEPTED
