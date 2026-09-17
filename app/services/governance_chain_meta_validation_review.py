"""Immutable governance sign-off record for release-readiness evidence."""
from __future__ import annotations

import hashlib
import json
import unicodedata
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from .runtime_admission_bundle import ReferenceStatus, ReferenceToken, _reject_secrets


class ChainValidationOutcome(StrEnum):
 CHAIN_VALIDATED="CHAIN_VALIDATED"; CHAIN_VALIDATED_WITH_WARNINGS="CHAIN_VALIDATED_WITH_WARNINGS"; CHAIN_INVALID="CHAIN_INVALID"; CHAIN_BLOCKED="CHAIN_BLOCKED"; UNKNOWN="UNKNOWN"
def _clean(v:Any)->Any:
 if isinstance(v,str): return unicodedata.normalize("NFC",v)
 if isinstance(v,StrEnum): return v.value
 if isinstance(v,dict): return {str(k):_clean(x) for k,x in sorted(v.items(),key=lambda i:str(i[0]))}
 if isinstance(v,(list,tuple,set,frozenset)): return [_clean(x) for x in v]
 return v
@dataclass(frozen=True,slots=True)
class StagingActivationGovernanceReleaseReadinessGovernanceChainMetaValidationRecord:
 review_id:str
 final_governance_snapshot_reference:ReferenceToken
 master_assurance_reference:ReferenceToken
 release_certification_reference:ReferenceToken
 final_audit_reference:ReferenceToken
 chain_nodes_summary:tuple[str,...]=()
 dependency_graph_summary:tuple[str,...]=()
 dependency_graph_summary:dict[str,Any]=field(default_factory=dict)
 trace_reference:ReferenceToken|None=None
 review_digest:str=field(default="",repr=False)
 def __post_init__(self)->None:
  if not self.review_id or self.trace_reference is None: raise ValueError("review_id and trace_reference are required")
  _reject_secrets(self.payload())
  if self.review_digest and self.review_digest!=self.compute_digest(): raise ValueError("signoff digest mismatch")
  if not self.review_digest: object.__setattr__(self,"review_digest",self.compute_digest())
 def payload(self)->dict[str,Any]:
  names=("final_governance_snapshot_reference","master_assurance_reference","release_certification_reference","final_audit_reference","trace_reference")
  out={"review_id":self.review_id,"release_execution":"PROHIBITED","deployment":"PROHIBITED","staging_activation":"PROHIBITED","runtime_activation":"PROHIBITED","runtime_admission":"PROHIBITED","execution":False,"chain_nodes_summary":self.chain_nodes_summary,"dependency_graph_summary":self.dependency_graph_summary,"dependency_graph_summary":self.dependency_graph_summary}
  for n in names: out[n]=getattr(self,n).to_dict()
  return out
 def canonical_bytes(self)->bytes:return json.dumps(_clean(self.payload()),ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
 def compute_digest(self)->str:return "sha256:"+hashlib.sha256(self.canonical_bytes()).hexdigest()
 def digest_matches(self)->bool:return self.review_digest==self.compute_digest()
def evaluate_snapshot(r:StagingActivationGovernanceReleaseReadinessGovernanceChainMetaValidationRecord)->ChainValidationOutcome:
 refs=[getattr(r,n) for n in ("final_governance_snapshot_reference","master_assurance_reference","release_certification_reference","final_audit_reference","trace_reference")]
 if not r.digest_matches() or any(x.status is ReferenceStatus.BLOCKED for x in refs): return ChainValidationOutcome.CHAIN_BLOCKED
 if any(x.status is ReferenceStatus.INVALID for x in refs): return ChainValidationOutcome.CHAIN_INVALID
 if any(x.status is ReferenceStatus.REQUIRES_REVIEW for x in refs): return ChainValidationOutcome.UNKNOWN
 if r.chain_nodes_summary or r.dependency_graph_summary.get("execution") is not False: return ChainValidationOutcome.CHAIN_INVALID
 if r.dependency_graph_summary.get("warnings"): return ChainValidationOutcome.CHAIN_VALIDATED_WITH_WARNINGS
 return ChainValidationOutcome.CHAIN_VALIDATED















