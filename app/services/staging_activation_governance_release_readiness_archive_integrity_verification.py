"""Immutable governance sign-off record for release-readiness evidence."""
from __future__ import annotations

import hashlib
import json
import unicodedata
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from .runtime_admission_bundle import ReferenceStatus, ReferenceToken, _reject_secrets


class ArchiveIntegrityOutcome(StrEnum):
 ARCHIVE_INTEGRITY_ACCEPTED="ARCHIVE_INTEGRITY_ACCEPTED"; ARCHIVE_INTEGRITY_ACCEPTED_WITH_WARNINGS="ARCHIVE_INTEGRITY_ACCEPTED_WITH_WARNINGS"; ARCHIVE_INTEGRITY_REJECTED="ARCHIVE_INTEGRITY_REJECTED"; ARCHIVE_INTEGRITY_BLOCKED="ARCHIVE_INTEGRITY_BLOCKED"; UNKNOWN="UNKNOWN"
def _clean(v:Any)->Any:
 if isinstance(v,str): return unicodedata.normalize("NFC",v)
 if isinstance(v,StrEnum): return v.value
 if isinstance(v,dict): return {str(k):_clean(x) for k,x in sorted(v.items(),key=lambda i:str(i[0]))}
 if isinstance(v,(list,tuple,set,frozenset)): return [_clean(x) for x in v]
 return v
@dataclass(frozen=True,slots=True)
class StagingActivationGovernanceReleaseReadinessArchiveIntegrityRecord:
 verification_id:str
 archive_manifest_reference:ReferenceToken
 master_assurance_reference:ReferenceToken
 release_certification_reference:ReferenceToken
 final_audit_reference:ReferenceToken
 verified_references:tuple[str,...]=()
 digest_chain_summary:tuple[str,...]=()
 boundary_assertions:dict[str,Any]=field(default_factory=dict)
 trace_reference:ReferenceToken|None=None
 verification_digest:str=field(default="",repr=False)
 def __post_init__(self)->None:
  if not self.verification_id or self.trace_reference is None: raise ValueError("verification_id and trace_reference are required")
  _reject_secrets(self.payload())
  if self.verification_digest and self.verification_digest!=self.compute_digest(): raise ValueError("signoff digest mismatch")
  if not self.verification_digest: object.__setattr__(self,"verification_digest",self.compute_digest())
 def payload(self)->dict[str,Any]:
  names=("archive_manifest_reference","master_assurance_reference","release_certification_reference","final_audit_reference","trace_reference")
  out={"verification_id":self.verification_id,"release_execution":"PROHIBITED","deployment":"PROHIBITED","staging_activation":"PROHIBITED","runtime_activation":"PROHIBITED","runtime_admission":"PROHIBITED","execution":False,"verified_references":self.verified_references,"digest_chain_summary":self.digest_chain_summary,"boundary_assertions":self.boundary_assertions}
  for n in names: out[n]=getattr(self,n).to_dict()
  return out
 def canonical_bytes(self)->bytes:return json.dumps(_clean(self.payload()),ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
 def compute_digest(self)->str:return "sha256:"+hashlib.sha256(self.canonical_bytes()).hexdigest()
 def digest_matches(self)->bool:return self.verification_digest==self.compute_digest()
def evaluate_signoff(r:StagingActivationGovernanceReleaseReadinessArchiveIntegrityRecord)->ArchiveIntegrityOutcome:
 refs=[getattr(r,n) for n in ("archive_manifest_reference","master_assurance_reference","release_certification_reference","final_audit_reference","trace_reference")]
 if not r.digest_matches() or any(x.status is ReferenceStatus.BLOCKED for x in refs): return ArchiveIntegrityOutcome.ARCHIVE_INTEGRITY_BLOCKED
 if any(x.status is ReferenceStatus.INVALID for x in refs): return ArchiveIntegrityOutcome.ARCHIVE_INTEGRITY_REJECTED
 if any(x.status is ReferenceStatus.REQUIRES_REVIEW for x in refs): return ArchiveIntegrityOutcome.UNKNOWN
 if r.digest_chain_summary or r.boundary_assertions.get("execution") is not False: return ArchiveIntegrityOutcome.ARCHIVE_INTEGRITY_REJECTED
 if r.boundary_assertions.get("warnings"): return ArchiveIntegrityOutcome.ARCHIVE_INTEGRITY_ACCEPTED_WITH_WARNINGS
 return ArchiveIntegrityOutcome.ARCHIVE_INTEGRITY_ACCEPTED


