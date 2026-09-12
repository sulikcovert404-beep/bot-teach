"""Pure immutable reconciliation contract for future execution observations."""
from __future__ import annotations
import hashlib,json,re,unicodedata
from dataclasses import dataclass,field
from enum import StrEnum
from typing import Any,Iterable
from .runtime_admission_bundle import ReferenceStatus,ReferenceToken
from .runtime_execution_lifecycle import ExecutionLifecycle,LifecycleState
from .runtime_execution_result import ExecutionResult,ExecutionResultStatus,validate_execution_result
class ReconciliationOutcome(StrEnum):
 CONSISTENT="CONSISTENT"; REQUIRES_RECONCILIATION="REQUIRES_RECONCILIATION"; BLOCKED="BLOCKED"; UNKNOWN="UNKNOWN"
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
class ReconciliationRequest:
 reconciliation_id:str; execution_reference:ReferenceToken; expected_state:LifecycleState; observed_state:LifecycleState; result_reference:ReferenceToken|None; evidence_references:tuple[ReferenceToken,...]; trace_reference:ReferenceToken; digest:str=field(default="",repr=False)
 def __post_init__(self)->None:
  if not self.reconciliation_id or not self.execution_reference or not self.trace_reference:raise ValueError("reconciliation identity and references are required")
  _reject(self.payload())
  if self.digest and self.digest!=self.compute_digest():raise ValueError("reconciliation digest mismatch")
  if not self.digest:object.__setattr__(self,"digest",self.compute_digest())
 def payload(self)->dict[str,Any]:
  ref=lambda x:x.to_dict() if x else None
  return {"reconciliation_id":self.reconciliation_id,"execution_reference":self.execution_reference.to_dict(),"expected_state":self.expected_state.value,"observed_state":self.observed_state.value,"result_reference":ref(self.result_reference),"evidence_references":[x.to_dict() for x in self.evidence_references],"trace_reference":self.trace_reference.to_dict()}
 def canonical_bytes(self)->bytes:return _canon(self.payload())
 def compute_digest(self)->str:return "sha256:"+hashlib.sha256(self.canonical_bytes()).hexdigest()
 def digest_matches(self)->bool:return self.digest==self.compute_digest()
def validate_reconciliation(request:ReconciliationRequest,lifecycle:ExecutionLifecycle|None=None,result:ExecutionResult|None=None)->ReconciliationOutcome:
 if not request.digest_matches():return ReconciliationOutcome.BLOCKED
 refs=(request.execution_reference,request.trace_reference,*request.evidence_references, *(() if request.result_reference is None else (request.result_reference,)))
 if any(r.status is not ReferenceStatus.VALID for r in refs):return ReconciliationOutcome.BLOCKED
 if request.observed_state is LifecycleState.UNKNOWN:return ReconciliationOutcome.UNKNOWN
 if lifecycle is not None:
  if not lifecycle.digest_matches() or lifecycle.execution_id!=request.execution_reference.name:return ReconciliationOutcome.BLOCKED
  if lifecycle.current_state is not request.expected_state:return ReconciliationOutcome.REQUIRES_RECONCILIATION
 if result is not None:
  if request.result_reference is None or request.result_reference.reference_id != result.execution_id or request.result_reference.digest!=result.result_digest or not validate_execution_result(result):return ReconciliationOutcome.BLOCKED
  state={ExecutionResultStatus.SUCCEEDED:LifecycleState.SUCCEEDED,ExecutionResultStatus.FAILED:LifecycleState.FAILED,ExecutionResultStatus.PARTIAL:LifecycleState.PARTIAL,ExecutionResultStatus.BLOCKED:LifecycleState.BLOCKED,ExecutionResultStatus.UNKNOWN:LifecycleState.UNKNOWN}[result.status]
  if request.observed_state is not state:return ReconciliationOutcome.REQUIRES_RECONCILIATION
 if request.expected_state is not request.observed_state:return ReconciliationOutcome.REQUIRES_RECONCILIATION
 return ReconciliationOutcome.CONSISTENT
def build_reconciliation(*,reconciliation_id:str,execution_reference:ReferenceToken,expected_state:LifecycleState,observed_state:LifecycleState,result_reference:ReferenceToken|None,evidence_references:Iterable[ReferenceToken],trace_reference:ReferenceToken)->ReconciliationRequest:
 return ReconciliationRequest(reconciliation_id,execution_reference,expected_state,observed_state,result_reference,tuple(evidence_references),trace_reference)

