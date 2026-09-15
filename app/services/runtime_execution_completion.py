"""Pure immutable completion semantics contract."""
from __future__ import annotations
import hashlib,json,re,unicodedata
from dataclasses import dataclass,field
from enum import StrEnum
from typing import Any
from collections.abc import Iterable
from .runtime_admission_bundle import ReferenceStatus,ReferenceToken
from .runtime_execution_lifecycle import ExecutionLifecycle,LifecycleState
from .runtime_execution_result import ExecutionResult,ExecutionResultStatus,validate_execution_result
from .runtime_execution_attestation import ExecutionAttestation,AttestationStatus,validate_attestation
class CompletionStatus(StrEnum):
 COMPLETED="COMPLETED"; COMPLETED_WITH_WARNINGS="COMPLETED_WITH_WARNINGS"; FAILED_COMPLETION="FAILED_COMPLETION"; UNKNOWN="UNKNOWN"
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
class ExecutionCompletion:
 completion_id:str; execution_reference:ReferenceToken; lifecycle_reference:ReferenceToken; result_reference:ReferenceToken; attestation_reference:ReferenceToken; evidence_references:tuple[ReferenceToken,...]; trace_reference:ReferenceToken; completion_digest:str=field(default="",repr=False)
 def __post_init__(self)->None:
  if not self.completion_id or not self.execution_reference or not self.lifecycle_reference or not self.result_reference or not self.attestation_reference or not self.evidence_references or not self.trace_reference:raise ValueError("completion identity and references are required")
  _reject(self.payload())
  if self.completion_digest and self.completion_digest!=self.compute_digest():raise ValueError("completion digest mismatch")
  if not self.completion_digest:object.__setattr__(self,"completion_digest",self.compute_digest())
 def payload(self)->dict[str,Any]:return {"completion_id":self.completion_id,"execution_reference":self.execution_reference.to_dict(),"lifecycle_reference":self.lifecycle_reference.to_dict(),"result_reference":self.result_reference.to_dict(),"attestation_reference":self.attestation_reference.to_dict(),"evidence_references":[x.to_dict() for x in self.evidence_references],"trace_reference":self.trace_reference.to_dict()}
 def canonical_bytes(self)->bytes:return _canon(self.payload())
 def compute_digest(self)->str:return "sha256:"+hashlib.sha256(self.canonical_bytes()).hexdigest()
 def digest_matches(self)->bool:return self.completion_digest==self.compute_digest()
def validate_completion(completion:ExecutionCompletion,lifecycle:ExecutionLifecycle|None=None,result:ExecutionResult|None=None,attestation:ExecutionAttestation|None=None)->CompletionStatus:
 if not completion.digest_matches():return CompletionStatus.FAILED_COMPLETION
 refs=(completion.execution_reference,completion.lifecycle_reference,completion.result_reference,completion.attestation_reference,*completion.evidence_references,completion.trace_reference)
 if any(x.status is not ReferenceStatus.VALID for x in refs):return CompletionStatus.FAILED_COMPLETION
 if lifecycle is None or result is None or attestation is None:return CompletionStatus.UNKNOWN
 if lifecycle.current_state in (LifecycleState.FAILED,LifecycleState.UNKNOWN):return CompletionStatus.FAILED_COMPLETION if lifecycle.current_state is LifecycleState.FAILED else CompletionStatus.UNKNOWN
 if lifecycle.current_state not in (LifecycleState.SUCCEEDED,LifecycleState.PARTIAL):return CompletionStatus.UNKNOWN
 if completion.result_reference.digest!=result.result_digest or not validate_execution_result(result):return CompletionStatus.FAILED_COMPLETION
 if completion.attestation_reference.digest!=attestation.attestation_digest or validate_attestation(attestation,result) is not AttestationStatus.VALID:return CompletionStatus.FAILED_COMPLETION
 if lifecycle.current_state is LifecycleState.PARTIAL:return CompletionStatus.COMPLETED_WITH_WARNINGS
 return CompletionStatus.COMPLETED
def build_completion(*,completion_id:str,execution_reference:ReferenceToken,lifecycle_reference:ReferenceToken,result_reference:ReferenceToken,attestation_reference:ReferenceToken,evidence_references:Iterable[ReferenceToken],trace_reference:ReferenceToken)->ExecutionCompletion:return ExecutionCompletion(completion_id,execution_reference,lifecycle_reference,result_reference,attestation_reference,tuple(evidence_references),trace_reference)
