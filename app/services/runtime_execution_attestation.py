"""Pure immutable attestation reference contract."""
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
from .runtime_execution_evidence_projection import (
 EvidenceValidityStatus,
 ExecutionEvidenceProjection,
 validate_evidence_projection,
)
from .runtime_execution_result import ExecutionResult, validate_execution_result


class AttestationStatus(StrEnum):
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
class ExecutionAttestation:
 attestation_id:str; execution_reference:ReferenceToken; result_reference:ReferenceToken; projection_references:tuple[ReferenceToken,...]; boundary_reference:ReferenceToken; trace_reference:ReferenceToken; validity_period_reference:ReferenceToken; attestation_digest:str=field(default="",repr=False)
 def __post_init__(self)->None:
  if not self.attestation_id or not self.execution_reference or not self.result_reference or not self.projection_references or not self.boundary_reference or not self.trace_reference or not self.validity_period_reference:raise ValueError("attestation identity and references are required")
  _reject(self.payload())
  if self.attestation_digest and self.attestation_digest!=self.compute_digest():raise ValueError("attestation digest mismatch")
  if not self.attestation_digest:object.__setattr__(self,"attestation_digest",self.compute_digest())
 def payload(self)->dict[str,Any]:return {"attestation_id":self.attestation_id,"execution_reference":self.execution_reference.to_dict(),"result_reference":self.result_reference.to_dict(),"projection_references":[x.to_dict() for x in self.projection_references],"boundary_reference":self.boundary_reference.to_dict(),"trace_reference":self.trace_reference.to_dict(),"validity_period_reference":self.validity_period_reference.to_dict()}
 def canonical_bytes(self)->bytes:return _canon(self.payload())
 def compute_digest(self)->str:return "sha256:"+hashlib.sha256(self.canonical_bytes()).hexdigest()
 def digest_matches(self)->bool:return self.attestation_digest==self.compute_digest()
def validate_attestation(attestation:ExecutionAttestation,result:ExecutionResult|None=None,projections:Iterable[ExecutionEvidenceProjection]|None=None)->AttestationStatus:
 if not attestation.digest_matches():return AttestationStatus.INVALID
 refs=(attestation.execution_reference,attestation.result_reference,*attestation.projection_references,attestation.boundary_reference,attestation.trace_reference,attestation.validity_period_reference)
 if any(r.status is not ReferenceStatus.VALID for r in refs):return AttestationStatus.INVALID
 if result is None or not validate_execution_result(result):return AttestationStatus.UNKNOWN
 if attestation.result_reference.reference_id!=result.execution_id or attestation.result_reference.digest!=result.result_digest:return AttestationStatus.INVALID
 if projections is None:return AttestationStatus.UNKNOWN
 ps=tuple(projections)
 if len(ps)!=len(attestation.projection_references):return AttestationStatus.INVALID
 for p,ref in zip(ps,attestation.projection_references):
  if ref.digest!=p.projection_digest or not validate_evidence_projection(p,result):return AttestationStatus.INVALID
 if any(p.validity_status is not EvidenceValidityStatus.VALID for p in ps):return AttestationStatus.INVALID
 return AttestationStatus.VALID
def build_attestation(*,attestation_id:str,execution_reference:ReferenceToken,result_reference:ReferenceToken,projection_references:Iterable[ReferenceToken],boundary_reference:ReferenceToken,trace_reference:ReferenceToken,validity_period_reference:ReferenceToken)->ExecutionAttestation:return ExecutionAttestation(attestation_id,execution_reference,result_reference,tuple(projection_references),boundary_reference,trace_reference,validity_period_reference)
