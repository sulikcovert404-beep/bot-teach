"""Immutable governance sign-off record for release-readiness evidence."""
from __future__ import annotations

import hashlib
import json
import unicodedata
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from .runtime_admission_bundle import ReferenceStatus, ReferenceToken, _reject_secrets


class ArchiveFinalPackageOutcome(StrEnum):
 ARCHIVE_ACCEPTED="ARCHIVE_ACCEPTED"; ARCHIVE_ACCEPTED_WITH_WARNINGS="ARCHIVE_ACCEPTED_WITH_WARNINGS"; ARCHIVE_REJECTED="ARCHIVE_REJECTED"; ARCHIVE_PACKAGE_BLOCKED="ARCHIVE_PACKAGE_BLOCKED"; UNKNOWN="UNKNOWN"
def _clean(v:Any)->Any:
 if isinstance(v,str): return unicodedata.normalize("NFC",v)
 if isinstance(v,StrEnum): return v.value
 if isinstance(v,dict): return {str(k):_clean(x) for k,x in sorted(v.items(),key=lambda i:str(i[0]))}
 if isinstance(v,(list,tuple,set,frozenset)): return [_clean(x) for x in v]
 return v
@dataclass(frozen=True,slots=True)
class StagingActivationGovernanceReleaseReadinessArchiveFinalPackageRecord:
 package_id:str
 archive_certification_reference:ReferenceToken
 master_assurance_reference:ReferenceToken
 release_certification_reference:ReferenceToken
 final_audit_reference:ReferenceToken
 archive_scope:tuple[str,...]=()
 historical_position:tuple[str,...]=()
 historical_position:dict[str,Any]=field(default_factory=dict)
 trace_reference:ReferenceToken|None=None
 package_digest:str=field(default="",repr=False)
 def __post_init__(self)->None:
  if not self.package_id or self.trace_reference is None: raise ValueError("package_id and trace_reference are required")
  _reject_secrets(self.payload())
  if self.package_digest and self.package_digest!=self.compute_digest(): raise ValueError("signoff digest mismatch")
  if not self.package_digest: object.__setattr__(self,"package_digest",self.compute_digest())
 def payload(self)->dict[str,Any]:
  names=("archive_certification_reference","master_assurance_reference","release_certification_reference","final_audit_reference","trace_reference")
  out={"package_id":self.package_id,"release_execution":"PROHIBITED","deployment":"PROHIBITED","staging_activation":"PROHIBITED","runtime_activation":"PROHIBITED","runtime_admission":"PROHIBITED","execution":False,"archive_scope":self.archive_scope,"historical_position":self.historical_position,"historical_position":self.historical_position}
  for n in names: out[n]=getattr(self,n).to_dict()
  return out
 def canonical_bytes(self)->bytes:return json.dumps(_clean(self.payload()),ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
 def compute_digest(self)->str:return "sha256:"+hashlib.sha256(self.canonical_bytes()).hexdigest()
 def digest_matches(self)->bool:return self.package_digest==self.compute_digest()
def evaluate_certification(r:StagingActivationGovernanceReleaseReadinessArchiveFinalPackageRecord)->ArchiveFinalPackageOutcome:
 refs=[getattr(r,n) for n in ("archive_certification_reference","master_assurance_reference","release_certification_reference","final_audit_reference","trace_reference")]
 if not r.digest_matches() or any(x.status is ReferenceStatus.BLOCKED for x in refs): return ArchiveFinalPackageOutcome.ARCHIVE_PACKAGE_BLOCKED
 if any(x.status is ReferenceStatus.INVALID for x in refs): return ArchiveFinalPackageOutcome.ARCHIVE_REJECTED
 if any(x.status is ReferenceStatus.REQUIRES_REVIEW for x in refs): return ArchiveFinalPackageOutcome.UNKNOWN
 if r.archive_scope or r.historical_position.get("execution") is not False: return ArchiveFinalPackageOutcome.ARCHIVE_REJECTED
 if r.historical_position.get("warnings"): return ArchiveFinalPackageOutcome.ARCHIVE_ACCEPTED_WITH_WARNINGS
 return ArchiveFinalPackageOutcome.ARCHIVE_ACCEPTED







