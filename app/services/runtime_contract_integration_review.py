"""Pure immutable review of the runtime contract dependency chain."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from .runtime_admission_bundle import ReferenceStatus, ReferenceToken


class IntegrationOutcome(StrEnum):
 COMPATIBLE="COMPATIBLE"; COMPATIBLE_WITH_WARNINGS="COMPATIBLE_WITH_WARNINGS"; INCOMPATIBLE="INCOMPATIBLE"; BLOCKED="BLOCKED"; UNKNOWN="UNKNOWN"
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
class ContractIntegrationReview:
 review_id:str; contract_references:tuple[ReferenceToken,...]; dependency_map:Mapping[str,tuple[str,...]]; compatibility_summary:str; violations:tuple[str,...]; risk_summary:str; trace_reference:ReferenceToken; review_digest:str=field(default="",repr=False)
 def __post_init__(self)->None:
  if not self.review_id or not self.contract_references or not self.compatibility_summary or not self.trace_reference:raise ValueError("review identity and fields are required")
  object.__setattr__(self,"dependency_map",{str(k):tuple(v) for k,v in self.dependency_map.items()})
  _reject(self.payload())
  if self.review_digest and self.review_digest!=self.compute_digest():raise ValueError("review digest mismatch")
  if not self.review_digest:object.__setattr__(self,"review_digest",self.compute_digest())
 def payload(self)->dict[str,Any]:return {"review_id":self.review_id,"contract_references":[x.to_dict() for x in self.contract_references],"dependency_map":self.dependency_map,"compatibility_summary":self.compatibility_summary,"violations":self.violations,"risk_summary":self.risk_summary,"trace_reference":self.trace_reference.to_dict()}
 def canonical_bytes(self)->bytes:return _canon(self.payload())
 def compute_digest(self)->str:return "sha256:"+hashlib.sha256(self.canonical_bytes()).hexdigest()
 def digest_matches(self)->bool:return self.review_digest==self.compute_digest()
def validate_integration_review(review:ContractIntegrationReview)->IntegrationOutcome:
 if not review.digest_matches() or review.trace_reference.status is not ReferenceStatus.VALID:return IntegrationOutcome.BLOCKED
 if any(x.status is not ReferenceStatus.VALID for x in review.contract_references):return IntegrationOutcome.BLOCKED
 keys=set(review.dependency_map)
 if any(dep not in keys for deps in review.dependency_map.values() for dep in deps):return IntegrationOutcome.INCOMPATIBLE
 if review.violations:return IntegrationOutcome.INCOMPATIBLE
 if review.risk_summary.strip():return IntegrationOutcome.COMPATIBLE_WITH_WARNINGS
 return IntegrationOutcome.COMPATIBLE
def build_integration_review(*,review_id:str,contract_references:tuple[ReferenceToken,...],dependency_map:Mapping[str,tuple[str,...]],compatibility_summary:str,violations:tuple[str,...],risk_summary:str,trace_reference:ReferenceToken)->ContractIntegrationReview:return ContractIntegrationReview(review_id,contract_references,dependency_map,compatibility_summary,violations,risk_summary,trace_reference)

