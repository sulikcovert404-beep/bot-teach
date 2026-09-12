"""Pure immutable lifecycle contract for future runtime executions."""
from __future__ import annotations
import hashlib, json, re, unicodedata
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Iterable
from .runtime_admission_bundle import ReferenceStatus, ReferenceToken
from .runtime_execution_boundary import ExecutionBoundaryContract
from .runtime_execution_result import ExecutionResult, ExecutionResultStatus, validate_execution_result

class LifecycleState(StrEnum):
    CREATED="CREATED"; ADMITTED="ADMITTED"; RUNNING="RUNNING"; SUCCEEDED="SUCCEEDED"; FAILED="FAILED"; PARTIAL="PARTIAL"; BLOCKED="BLOCKED"; CANCELLED="CANCELLED"; UNKNOWN="UNKNOWN"
class LifecycleOutcome(StrEnum):
    VALID="VALID"; INVALID="INVALID"; BLOCKED="BLOCKED"; REQUIRES_REVIEW="REQUIRES_REVIEW"
_SECRET=re.compile(r"(?i)(api[_-]?key|token|password|secret|credential|authorization|private[_-]?key)")
_TERMINAL=frozenset({LifecycleState.SUCCEEDED,LifecycleState.FAILED,LifecycleState.CANCELLED})
_TRANSITIONS={
 LifecycleState.CREATED:frozenset({LifecycleState.ADMITTED,LifecycleState.BLOCKED,LifecycleState.UNKNOWN,LifecycleState.CANCELLED}),
 LifecycleState.ADMITTED:frozenset({LifecycleState.RUNNING,LifecycleState.BLOCKED,LifecycleState.UNKNOWN,LifecycleState.CANCELLED}),
 LifecycleState.RUNNING:frozenset({LifecycleState.SUCCEEDED,LifecycleState.FAILED,LifecycleState.PARTIAL,LifecycleState.BLOCKED,LifecycleState.UNKNOWN,LifecycleState.CANCELLED}),
 LifecycleState.PARTIAL:frozenset({LifecycleState.RUNNING,LifecycleState.SUCCEEDED,LifecycleState.FAILED,LifecycleState.BLOCKED,LifecycleState.UNKNOWN}),
 LifecycleState.BLOCKED:frozenset({LifecycleState.ADMITTED,LifecycleState.UNKNOWN}),
 LifecycleState.UNKNOWN:frozenset({LifecycleState.ADMITTED,LifecycleState.RUNNING,LifecycleState.FAILED,LifecycleState.BLOCKED,LifecycleState.CANCELLED}),
 LifecycleState.SUCCEEDED:frozenset(), LifecycleState.FAILED:frozenset(), LifecycleState.CANCELLED:frozenset(),
}
def _clean(v:Any)->Any:
 if isinstance(v,str): return unicodedata.normalize("NFC",v)
 if isinstance(v,StrEnum): return v.value
 if isinstance(v,dict): return {str(k):_clean(x) for k,x in sorted(v.items(),key=lambda i:str(i[0]))}
 if isinstance(v,(tuple,list,set,frozenset)): return sorted((_clean(x) for x in v),key=lambda x:json.dumps(x,ensure_ascii=False,sort_keys=True))
 return v
def _reject(v:Any)->None:
 if isinstance(v,str) and _SECRET.search(v): raise ValueError("secret-like content is not permitted")
 if isinstance(v,dict):
  for k,x in v.items():
   if _SECRET.search(str(k)): raise ValueError("secret-like field is not permitted")
   _reject(x)
 elif isinstance(v,(tuple,list,set,frozenset)):
  for x in v:_reject(x)
def _canonical(v:Any)->bytes:return json.dumps(_clean(v),ensure_ascii=False,sort_keys=True,separators=(",",":" )).encode("utf-8")
@dataclass(frozen=True,slots=True)
class ExecutionLifecycle:
 execution_id:str; current_state:LifecycleState; previous_state:LifecycleState|None; transition_reference:ReferenceToken; boundary_reference:ReferenceToken; result_reference:ReferenceToken|None; trace_reference:ReferenceToken; lifecycle_digest:str=field(default="",repr=False)
 def __post_init__(self)->None:
  if not self.execution_id or not self.transition_reference or not self.boundary_reference or not self.trace_reference: raise ValueError("execution and lifecycle references are required")
  _reject(self.payload())
  if self.lifecycle_digest and self.lifecycle_digest!=self.compute_digest(): raise ValueError("lifecycle digest mismatch")
  if not self.lifecycle_digest: object.__setattr__(self,"lifecycle_digest",self.compute_digest())
 def payload(self)->dict[str,Any]:
  ref=lambda x:x.to_dict() if x else None
  return {"execution_id":self.execution_id,"current_state":self.current_state.value,"previous_state":self.previous_state.value if self.previous_state else None,"transition_reference":self.transition_reference.to_dict(),"boundary_reference":self.boundary_reference.to_dict(),"result_reference":ref(self.result_reference),"trace_reference":self.trace_reference.to_dict()}
 def canonical_bytes(self)->bytes:return _canonical(self.payload())
 def compute_digest(self)->str:return "sha256:"+hashlib.sha256(self.canonical_bytes()).hexdigest()
 def digest_matches(self)->bool:return self.lifecycle_digest==self.compute_digest()
def validate_execution_lifecycle(lifecycle:ExecutionLifecycle,result:ExecutionResult|None=None,boundary:ExecutionBoundaryContract|None=None)->LifecycleOutcome:
 if not lifecycle.digest_matches(): return LifecycleOutcome.INVALID
 if lifecycle.trace_reference.status is not ReferenceStatus.VALID or lifecycle.boundary_reference.status is not ReferenceStatus.VALID: return LifecycleOutcome.INVALID
 if lifecycle.previous_state is not None and lifecycle.current_state not in _TRANSITIONS.get(lifecycle.previous_state,frozenset()): return LifecycleOutcome.INVALID
 if lifecycle.current_state in {LifecycleState.SUCCEEDED,LifecycleState.FAILED,LifecycleState.PARTIAL} and lifecycle.result_reference is None:return LifecycleOutcome.INVALID
 if lifecycle.current_state is LifecycleState.BLOCKED:return LifecycleOutcome.BLOCKED
 if result is not None:
  if lifecycle.result_reference is None or lifecycle.result_reference.digest!=result.result_digest or not validate_execution_result(result,boundary):return LifecycleOutcome.INVALID
  expected={ExecutionResultStatus.SUCCEEDED:LifecycleState.SUCCEEDED,ExecutionResultStatus.FAILED:LifecycleState.FAILED,ExecutionResultStatus.PARTIAL:LifecycleState.PARTIAL,ExecutionResultStatus.BLOCKED:LifecycleState.BLOCKED,ExecutionResultStatus.UNKNOWN:LifecycleState.UNKNOWN}[result.status]
  if lifecycle.current_state is not expected:return LifecycleOutcome.INVALID
 if boundary is not None and (not boundary.digest_matches() or lifecycle.boundary_reference.digest!=boundary.boundary_digest):return LifecycleOutcome.INVALID
 return LifecycleOutcome.VALID
def build_execution_lifecycle(*,execution_id:str,current_state:LifecycleState,previous_state:LifecycleState|None,transition_reference:ReferenceToken,boundary_reference:ReferenceToken,result_reference:ReferenceToken|None,trace_reference:ReferenceToken)->ExecutionLifecycle:
 return ExecutionLifecycle(execution_id,current_state,previous_state,transition_reference,boundary_reference,result_reference,trace_reference)
