"""Pure immutable readiness snapshot contract."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from .runtime_admission_bundle import ReferenceStatus, ReferenceToken


class SnapshotStatus(StrEnum):
 READY="READY"; READY_WITH_WARNINGS="READY_WITH_WARNINGS"; NOT_READY="NOT_READY"; BLOCKED="BLOCKED"; UNKNOWN="UNKNOWN"
_SECRET=re.compile(r"(?i)(api[_-]?key|token|password|secret|credential|authorization|private[_-]?key)")
def _clean(v:Any)->Any:
 if isinstance(v,str):return unicodedata.normalize("NFC",v)
 if isinstance(v,StrEnum):return v.value
 if isinstance(v,dict):return {str(k):_clean(x) for k,x in sorted(v.items(),key=lambda i:str(i[0]))}
 if isinstance(v,(tuple,list,set,frozenset)):return sorted((_clean(x) for x in v),key=lambda x:json.dumps(x,ensure_ascii=False,sort_keys=True))
 return v
def _reject(v:Any)->None:
 if isinstance(v,str) and _SECRET.search(v):raise ValueError("secret-like content is not permitted")
 if isinstance(v,dict):
  for k,x in v.items():
   if _SECRET.search(str(k)):raise ValueError("secret-like field is not permitted")
   _reject(x)
 elif isinstance(v,(tuple,list,set,frozenset)):
  for x in v:_reject(x)
def _canon(v:Any)->bytes:return json.dumps(_clean(v),ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
@dataclass(frozen=True,slots=True)
class RuntimeContractReadinessSnapshot:
 snapshot_id:str; evaluated_contracts:tuple[ReferenceToken,...]; integration_review_reference:ReferenceToken; release_readiness_reference:ReferenceToken; evidence_references:tuple[ReferenceToken,...]; trace_reference:ReferenceToken; snapshot_timestamp_reference:ReferenceToken; snapshot_digest:str=field(default="",repr=False)
 def __post_init__(self)->None:
  if not self.snapshot_id or not self.evaluated_contracts or not self.integration_review_reference or not self.release_readiness_reference or not self.evidence_references or not self.trace_reference or not self.snapshot_timestamp_reference:raise ValueError("snapshot identity and references are required")
  _reject(self.payload())
  if self.snapshot_digest and self.snapshot_digest!=self.compute_digest():raise ValueError("snapshot digest mismatch")
  if not self.snapshot_digest:object.__setattr__(self,"snapshot_digest",self.compute_digest())
 def payload(self)->dict[str,Any]:return {"snapshot_id":self.snapshot_id,"evaluated_contracts":[x.to_dict() for x in self.evaluated_contracts],"integration_review_reference":self.integration_review_reference.to_dict(),"release_readiness_reference":self.release_readiness_reference.to_dict(),"evidence_references":[x.to_dict() for x in self.evidence_references],"trace_reference":self.trace_reference.to_dict(),"snapshot_timestamp_reference":self.snapshot_timestamp_reference.to_dict()}
 def canonical_bytes(self)->bytes:return _canon(self.payload())
 def compute_digest(self)->str:return "sha256:"+hashlib.sha256(self.canonical_bytes()).hexdigest()
 def digest_matches(self)->bool:return self.snapshot_digest==self.compute_digest()
def validate_snapshot(snapshot:RuntimeContractReadinessSnapshot,status:SnapshotStatus)->bool:
 if not snapshot.digest_matches():return False
 refs=(*snapshot.evaluated_contracts,snapshot.integration_review_reference,snapshot.release_readiness_reference,*snapshot.evidence_references,snapshot.trace_reference,snapshot.snapshot_timestamp_reference)
 if any(x.status is not ReferenceStatus.VALID for x in refs):return status in (SnapshotStatus.BLOCKED,SnapshotStatus.NOT_READY,SnapshotStatus.UNKNOWN)
 return not (status is SnapshotStatus.READY and (not snapshot.evaluated_contracts or not snapshot.evidence_references))
def build_snapshot(*,snapshot_id:str,evaluated_contracts:Iterable[ReferenceToken],integration_review_reference:ReferenceToken,release_readiness_reference:ReferenceToken,evidence_references:Iterable[ReferenceToken],trace_reference:ReferenceToken,snapshot_timestamp_reference:ReferenceToken)->RuntimeContractReadinessSnapshot:return RuntimeContractReadinessSnapshot(snapshot_id,tuple(evaluated_contracts),integration_review_reference,release_readiness_reference,tuple(evidence_references),trace_reference,snapshot_timestamp_reference)
