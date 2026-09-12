"""Pure immutable projection from execution results to future evidence references."""
from __future__ import annotations
import hashlib,json,re,unicodedata
from dataclasses import dataclass,field
from enum import StrEnum
from typing import Any
from .runtime_admission_bundle import ReferenceStatus,ReferenceToken
from .runtime_execution_result import ExecutionResult,ExecutionResultStatus,validate_execution_result
class EvidenceValidityStatus(StrEnum):
 VALID="VALID"; INVALID="INVALID"; EXPIRED="EXPIRED"; UNKNOWN="UNKNOWN"
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
class ExecutionEvidenceProjection:
 projection_id:str; execution_reference:ReferenceToken; result_reference:ReferenceToken; evidence_type:str; evidence_payload_reference:ReferenceToken; validity_status:EvidenceValidityStatus; trace_reference:ReferenceToken; projection_digest:str=field(default="",repr=False)
 def __post_init__(self)->None:
  if not self.projection_id or not self.execution_reference or not self.result_reference or not self.evidence_type or not self.evidence_payload_reference or not self.trace_reference:raise ValueError("projection identity and references are required")
  _reject(self.payload())
  if self.projection_digest and self.projection_digest!=self.compute_digest():raise ValueError("projection digest mismatch")
  if not self.projection_digest:object.__setattr__(self,"projection_digest",self.compute_digest())
 def payload(self)->dict[str,Any]:return {"projection_id":self.projection_id,"execution_reference":self.execution_reference.to_dict(),"result_reference":self.result_reference.to_dict(),"evidence_type":self.evidence_type,"evidence_payload_reference":self.evidence_payload_reference.to_dict(),"validity_status":self.validity_status.value,"trace_reference":self.trace_reference.to_dict()}
 def canonical_bytes(self)->bytes:return _canon(self.payload())
 def compute_digest(self)->str:return "sha256:"+hashlib.sha256(self.canonical_bytes()).hexdigest()
 def digest_matches(self)->bool:return self.projection_digest==self.compute_digest()
def validate_evidence_projection(projection:ExecutionEvidenceProjection,result:ExecutionResult|None=None)->bool:
 if not projection.digest_matches():return False
 refs=(projection.execution_reference,projection.result_reference,projection.evidence_payload_reference,projection.trace_reference)
 if any(r.status is not ReferenceStatus.VALID for r in refs):return False
 if projection.validity_status is EvidenceValidityStatus.VALID:
  if result is None or not validate_execution_result(result):return False
  if projection.result_reference.reference_id!=result.execution_id or projection.result_reference.digest!=result.result_digest:return False
  if result.status in (ExecutionResultStatus.BLOCKED,ExecutionResultStatus.UNKNOWN):return False
 return True
def build_evidence_projection(*,projection_id:str,execution_reference:ReferenceToken,result_reference:ReferenceToken,evidence_type:str,evidence_payload_reference:ReferenceToken,validity_status:EvidenceValidityStatus,trace_reference:ReferenceToken)->ExecutionEvidenceProjection:return ExecutionEvidenceProjection(projection_id,execution_reference,result_reference,evidence_type,evidence_payload_reference,validity_status,trace_reference)
