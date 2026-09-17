"""Immutable governance sign-off record for release-readiness evidence."""
from __future__ import annotations

import hashlib
import json
import unicodedata
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from .runtime_admission_bundle import ReferenceStatus, ReferenceToken, _reject_secrets


class FinalSnapshotOutcome(StrEnum):
 FINAL_SNAPSHOT_CONFIRMED="FINAL_SNAPSHOT_CONFIRMED"; FINAL_SNAPSHOT_CONFIRMED_WITH_WARNINGS="FINAL_SNAPSHOT_CONFIRMED_WITH_WARNINGS"; FINAL_SNAPSHOT_NOT_READY="FINAL_SNAPSHOT_NOT_READY"; FINAL_SNAPSHOT_BLOCKED="FINAL_SNAPSHOT_BLOCKED"; UNKNOWN="UNKNOWN"
def _clean(v:Any)->Any:
 if isinstance(v,str): return unicodedata.normalize("NFC",v)
 if isinstance(v,StrEnum): return v.value
 if isinstance(v,dict): return {str(k):_clean(x) for k,x in sorted(v.items(),key=lambda i:str(i[0]))}
 if isinstance(v,(list,tuple,set,frozenset)): return [_clean(x) for x in v]
 return v
@dataclass(frozen=True,slots=True)
class StagingActivationGovernanceReleaseReadinessFinalGovernanceSnapshotRecord:
 snapshot_id:str
 archive_closure_decision_reference:ReferenceToken
 master_assurance_reference:ReferenceToken
 release_certification_reference:ReferenceToken
 final_audit_reference:ReferenceToken
 snapshot_position:tuple[str,...]=()
 snapshot_summary:tuple[str,...]=()
 snapshot_summary:dict[str,Any]=field(default_factory=dict)
 trace_reference:ReferenceToken|None=None
 snapshot_digest:str=field(default="",repr=False)
 def __post_init__(self)->None:
  if not self.snapshot_id or self.trace_reference is None: raise ValueError("snapshot_id and trace_reference are required")
  _reject_secrets(self.payload())
  if self.snapshot_digest and self.snapshot_digest!=self.compute_digest(): raise ValueError("signoff digest mismatch")
  if not self.snapshot_digest: object.__setattr__(self,"snapshot_digest",self.compute_digest())
 def payload(self)->dict[str,Any]:
  names=("archive_closure_decision_reference","master_assurance_reference","release_certification_reference","final_audit_reference","trace_reference")
  out={"snapshot_id":self.snapshot_id,"release_execution":"PROHIBITED","deployment":"PROHIBITED","staging_activation":"PROHIBITED","runtime_activation":"PROHIBITED","runtime_admission":"PROHIBITED","execution":False,"snapshot_position":self.snapshot_position,"snapshot_summary":self.snapshot_summary,"snapshot_summary":self.snapshot_summary}
  for n in names: out[n]=getattr(self,n).to_dict()
  return out
 def canonical_bytes(self)->bytes:return json.dumps(_clean(self.payload()),ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
 def compute_digest(self)->str:return "sha256:"+hashlib.sha256(self.canonical_bytes()).hexdigest()
 def digest_matches(self)->bool:return self.snapshot_digest==self.compute_digest()
def evaluate_snapshot(r:StagingActivationGovernanceReleaseReadinessFinalGovernanceSnapshotRecord)->FinalSnapshotOutcome:
 refs=[getattr(r,n) for n in ("archive_closure_decision_reference","master_assurance_reference","release_certification_reference","final_audit_reference","trace_reference")]
 if not r.digest_matches() or any(x.status is ReferenceStatus.BLOCKED for x in refs): return FinalSnapshotOutcome.FINAL_SNAPSHOT_BLOCKED
 if any(x.status is ReferenceStatus.INVALID for x in refs): return FinalSnapshotOutcome.FINAL_SNAPSHOT_NOT_READY
 if any(x.status is ReferenceStatus.REQUIRES_REVIEW for x in refs): return FinalSnapshotOutcome.UNKNOWN
 if r.snapshot_position or r.snapshot_summary.get("execution") is not False: return FinalSnapshotOutcome.FINAL_SNAPSHOT_NOT_READY
 if r.snapshot_summary.get("warnings"): return FinalSnapshotOutcome.FINAL_SNAPSHOT_CONFIRMED_WITH_WARNINGS
 return FinalSnapshotOutcome.FINAL_SNAPSHOT_CONFIRMED













