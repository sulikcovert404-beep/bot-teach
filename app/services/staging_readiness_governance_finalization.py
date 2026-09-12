from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum
import hashlib, json, unicodedata

class FinalizationOutcome(StrEnum):
    STAGING_GOVERNANCE_FINALIZED='STAGING_GOVERNANCE_FINALIZED'
    STAGING_GOVERNANCE_FINALIZED_WITH_WARNINGS='STAGING_GOVERNANCE_FINALIZED_WITH_WARNINGS'
    STAGING_GOVERNANCE_NOT_FINALIZED='STAGING_GOVERNANCE_NOT_FINALIZED'
    STAGING_GOVERNANCE_BLOCKED='STAGING_GOVERNANCE_BLOCKED'
    UNKNOWN='UNKNOWN'

def _n(v: str) -> str: return unicodedata.normalize('NFC', str(v)).strip()

@dataclass(frozen=True, slots=True)
class StagingReadinessGovernanceFinalization:
    finalization_id: str
    staging_entry_review_reference: str
    pre_staging_package_reference: str
    validation_assurance_reference: str
    activation_control_plane_reference: str
    activation_decision_reference: str
    governance_closure_reference: str
    baseline_freeze_reference: str
    final_findings: tuple[str, ...]
    boundary_assertions: tuple[str, ...]
    trace_reference: str
    finalization_digest: str = ''
    def __post_init__(self):
        for name in ('finalization_id','staging_entry_review_reference','pre_staging_package_reference','validation_assurance_reference','activation_control_plane_reference','activation_decision_reference','governance_closure_reference','baseline_freeze_reference','trace_reference'):
            value=_n(getattr(self,name))
            if not value or any(x in value.lower() for x in ('secret','password','api_key','bearer ')): raise ValueError(f'invalid {name}')
            object.__setattr__(self,name,value)
        object.__setattr__(self,'final_findings',tuple(_n(x) for x in self.final_findings))
        object.__setattr__(self,'boundary_assertions',tuple(_n(x) for x in self.boundary_assertions))
        digest=self.canonical_digest()
        if self.finalization_digest and self.finalization_digest != digest: raise ValueError('finalization digest mismatch')
        object.__setattr__(self,'finalization_digest',digest)
    def payload(self):
        return {k:getattr(self,k) for k in ('finalization_id','staging_entry_review_reference','pre_staging_package_reference','validation_assurance_reference','activation_control_plane_reference','activation_decision_reference','governance_closure_reference','baseline_freeze_reference','final_findings','boundary_assertions','trace_reference')} | {'staging_execution':'PROHIBITED','deployment':'PROHIBITED','runtime_activation':'PROHIBITED','runtime_admission':'PROHIBITED','execution':False}
    def canonical_digest(self): return hashlib.sha256(json.dumps(self.payload(),ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    @staticmethod
    def evaluate(*, references: tuple[str,...], findings: tuple[str,...]=(), assertions: tuple[str,...]=()):
        refs=tuple(_n(x) for x in references)
        if not refs or any(not x for x in refs) or any(k in x.upper() for x in refs for k in ('BLOCKED','DIGEST_MISMATCH','TRACE_FAILURE','BROKEN_LINEAGE')): return FinalizationOutcome.STAGING_GOVERNANCE_BLOCKED
        if any(k in x.upper() for x in refs for k in ('INVALID','CONTRADICTION')): return FinalizationOutcome.STAGING_GOVERNANCE_NOT_FINALIZED
        if any('UNKNOWN' in x.upper() for x in refs): return FinalizationOutcome.UNKNOWN
        allowed={'STAGING_EXECUTION=PROHIBITED','DEPLOYMENT=PROHIBITED','RUNTIME_ACTIVATION=PROHIBITED','RUNTIME_ADMISSION=PROHIBITED','EXECUTION=FALSE'}
        if any(_n(x).upper() not in allowed for x in assertions): return FinalizationOutcome.STAGING_GOVERNANCE_NOT_FINALIZED
        return FinalizationOutcome.STAGING_GOVERNANCE_FINALIZED_WITH_WARNINGS if findings else FinalizationOutcome.STAGING_GOVERNANCE_FINALIZED
