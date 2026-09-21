from __future__ import annotations

import hashlib
import json
import unicodedata
from dataclasses import dataclass
from enum import StrEnum


class AssuranceOutcome(StrEnum):
 ASSURANCE_READY='ASSURANCE_READY'; ASSURANCE_READY_WITH_WARNINGS='ASSURANCE_READY_WITH_WARNINGS'; ASSURANCE_NOT_READY='ASSURANCE_NOT_READY'; ASSURANCE_BLOCKED='ASSURANCE_BLOCKED'; UNKNOWN='UNKNOWN'
def _c(v:str)->str:return unicodedata.normalize('NFC',str(v)).strip()
@dataclass(frozen=True,slots=True)
class RuntimeActivationStagingValidationAssurance:
 assurance_id:str; staging_validation_framework_reference:str; staging_evidence_governance_reference:str; final_readiness_review_reference:str; activation_decision_reference:str; readiness_baseline_freeze_reference:str; assurance_findings:tuple[str,...]; trace_reference:str; assurance_digest:str=''
 def __post_init__(self) -> None:
  for n in ('assurance_id','staging_validation_framework_reference','staging_evidence_governance_reference','final_readiness_review_reference','activation_decision_reference','readiness_baseline_freeze_reference','trace_reference'):
   v=_c(getattr(self,n))
   if not v or any(x in v.lower() for x in ('secret','password','api_key','bearer ')): raise ValueError(f'invalid {n}')
   object.__setattr__(self,n,v)
  object.__setattr__(self,'assurance_findings',tuple(_c(x) for x in self.assurance_findings)); d=self.canonical_digest()
  if self.assurance_digest and self.assurance_digest!=d: raise ValueError('assurance digest mismatch')
  object.__setattr__(self,'assurance_digest',d)
 def payload(self) -> dict[str, object]: return {'assurance_id':self.assurance_id,'staging_validation_framework_reference':self.staging_validation_framework_reference,'staging_evidence_governance_reference':self.staging_evidence_governance_reference,'final_readiness_review_reference':self.final_readiness_review_reference,'activation_decision_reference':self.activation_decision_reference,'readiness_baseline_freeze_reference':self.readiness_baseline_freeze_reference,'assurance_findings':self.assurance_findings,'trace_reference':self.trace_reference,'runtime_activation':'PROHIBITED','runtime_admission':'PROHIBITED','execution':False}
 def canonical_digest(self) -> str: return hashlib.sha256(json.dumps(self.payload(),ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
 @staticmethod
 def evaluate(*,references:tuple[str,...],findings:tuple[str,...]=()) -> AssuranceOutcome:
  r=tuple(_c(x) for x in references)
  if not r or any(not x for x in r) or any(k in x.upper() for x in r for k in ('BLOCKED','DIGEST_MISMATCH','TRACE_FAILURE')): return AssuranceOutcome.ASSURANCE_BLOCKED
  if any(k in x.upper() for x in r for k in ('INVALID','CONTRADICTION')): return AssuranceOutcome.ASSURANCE_NOT_READY
  if any('UNKNOWN' in x.upper() for x in r): return AssuranceOutcome.UNKNOWN
  return AssuranceOutcome.ASSURANCE_READY_WITH_WARNINGS if findings else AssuranceOutcome.ASSURANCE_READY
