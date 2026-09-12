"""Pure immutable closure review of the admin contract chain."""
from __future__ import annotations
import hashlib,json,re,unicodedata
from dataclasses import dataclass,field
from enum import StrEnum
from typing import Any,Mapping,Iterable
from .runtime_admission_bundle import ReferenceStatus,ReferenceToken
class ClosureOutcome(StrEnum):
 CLOSED="CLOSED"; CLOSED_WITH_WARNINGS="CLOSED_WITH_WARNINGS"; OPEN="OPEN"; BLOCKED="BLOCKED"; UNKNOWN="UNKNOWN"
_SECRET=re.compile(r"(?i)(api[_-]?key|token|password|secret|credential|authorization|private[_-]?key)")
def _clean(v:Any)->Any:
 if isinstance(v,str): return unicodedata.normalize("NFC",v)
 if isinstance(v,StrEnum): return v.value
 if isinstance(v,Mapping): return {str(k):_clean(x) for k,x in sorted(v.items(),key=lambda i:str(i[0]))}
 if isinstance(v,(tuple,list,set,frozenset)): return sorted((_clean(x) for x in v),key=lambda x:json.dumps(x,ensure_ascii=False,sort_keys=True))
 return v
def _reject(v:Any)->None:
 if isinstance(v,str) and _SECRET.search(v): raise ValueError("secret-like content is not permitted")
 if isinstance(v,Mapping):
  for k,x in v.items():
   if _SECRET.search(str(k)): raise ValueError("secret-like field is not permitted")
   _reject(x)
 elif isinstance(v,(tuple,list,set,frozenset)):
  for x in v:_reject(x)
def _canon(v:Any)->bytes:return json.dumps(_clean(v),ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")
@dataclass(frozen=True,slots=True)
class ContractClosureReview:
 closure_id:str; evaluated_contracts:tuple[ReferenceToken,...]; dependency_graph:Mapping[str,tuple[str,...]]; authority_map:Mapping[str,str]; version_summary:Mapping[str,str]; digest_summary:Mapping[str,str]; trace_reference:ReferenceToken; closure_digest:str=field(default="",repr=False)
 def __post_init__(self)->None:
  if not self.closure_id or not self.evaluated_contracts or not self.trace_reference: raise ValueError("closure identity and references are required")
  object.__setattr__(self,"dependency_graph",{str(k):tuple(v) for k,v in self.dependency_graph.items()})
  object.__setattr__(self,"authority_map",dict(self.authority_map)); object.__setattr__(self,"version_summary",dict(self.version_summary)); object.__setattr__(self,"digest_summary",dict(self.digest_summary))
  _reject(self.payload())
  if self.closure_digest and self.closure_digest!=self.compute_digest(): raise ValueError("closure digest mismatch")
  if not self.closure_digest: object.__setattr__(self,"closure_digest",self.compute_digest())
 def payload(self)->dict[str,Any]: return {"closure_id":self.closure_id,"evaluated_contracts":[x.to_dict() for x in self.evaluated_contracts],"dependency_graph":self.dependency_graph,"authority_map":self.authority_map,"version_summary":self.version_summary,"digest_summary":self.digest_summary,"trace_reference":self.trace_reference.to_dict()}
 def canonical_bytes(self)->bytes:return _canon(self.payload())
 def compute_digest(self)->str:return "sha256:"+hashlib.sha256(self.canonical_bytes()).hexdigest()
 def digest_matches(self)->bool:return self.closure_digest==self.compute_digest()
def _cycle(graph:Mapping[str,tuple[str,...]])->bool:
 state:dict[str,int]={}
 def visit(n:str)->bool:
  if state.get(n)==1:return True
  if state.get(n)==2:return False
  state[n]=1
  for child in graph.get(n,()):
   if child not in graph or visit(child):return True
  state[n]=2; return False
 return any(visit(n) for n in graph)
def validate_closure(review:ContractClosureReview)->ClosureOutcome:
 if not review.digest_matches():return ClosureOutcome.BLOCKED
 if review.trace_reference.status is ReferenceStatus.REQUIRES_REVIEW:return ClosureOutcome.UNKNOWN
 if review.trace_reference.status is not ReferenceStatus.VALID:return ClosureOutcome.BLOCKED
 if any(r.status is not ReferenceStatus.VALID for r in review.evaluated_contracts):return ClosureOutcome.OPEN
 if _cycle(review.dependency_graph):return ClosureOutcome.BLOCKED
 if any(src==dst for src,ds in review.dependency_graph.items() for dst in ds):return ClosureOutcome.BLOCKED
 if len(review.authority_map)!=len(set(review.authority_map.values())):return ClosureOutcome.BLOCKED
 names={r.reference_id for r in review.evaluated_contracts}
 if set(review.dependency_graph)-names or any(d not in names for ds in review.dependency_graph.values() for d in ds):return ClosureOutcome.OPEN
 if not review.version_summary or any(not v for v in review.version_summary.values()):return ClosureOutcome.OPEN
 if len(set(review.version_summary.values()))>1:return ClosureOutcome.OPEN
 if set(review.digest_summary)-names or any(not v for v in review.digest_summary.values()):return ClosureOutcome.BLOCKED
 expected={r.reference_id:r.digest for r in review.evaluated_contracts}
 if any(review.digest_summary.get(n)!=d for n,d in expected.items()):return ClosureOutcome.BLOCKED
 if review.trace_reference.status is ReferenceStatus.REQUIRES_REVIEW:return ClosureOutcome.UNKNOWN
 if any(r.status is ReferenceStatus.REQUIRES_REVIEW for r in review.evaluated_contracts):return ClosureOutcome.UNKNOWN
 return ClosureOutcome.CLOSED
def build_closure_review(*,closure_id:str,evaluated_contracts:Iterable[ReferenceToken],dependency_graph:Mapping[str,tuple[str,...]],authority_map:Mapping[str,str],version_summary:Mapping[str,str],digest_summary:Mapping[str,str],trace_reference:ReferenceToken)->ContractClosureReview:return ContractClosureReview(closure_id,tuple(evaluated_contracts),dependency_graph,authority_map,version_summary,digest_summary,trace_reference)



