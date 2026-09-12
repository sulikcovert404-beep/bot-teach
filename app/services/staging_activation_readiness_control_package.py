from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum
import hashlib, json, unicodedata

class StagingControlOutcome(StrEnum):
    STAGING_CONTROL_READY='STAGING_CONTROL_READY'; STAGING_CONTROL_READY_WITH_WARNINGS='STAGING_CONTROL_READY_WITH_WARNINGS'; STAGING_CONTROL_NOT_READY='STAGING_CONTROL_NOT_READY'; STAGING_CONTROL_BLOCKED='STAGING_CONTROL_BLOCKED'; UNKNOWN='UNKNOWN'
def _n(v: str) -> str: return unicodedata.normalize('NFC', str(v)).strip()
@dataclass(frozen=True, slots=True)
class StagingActivationReadinessControlPackage:
    package_id: str
    staging_governance_finalization_reference: str
    staging_entry_review_reference: str
    pre_staging_package_reference: str
    activation_control_plane_reference: str
    activation_decision_reference: str
    readiness_assurance_reference: str
    evidence_governance_reference: str
    control_findings: tuple[str,...]
    boundary_assertions: tuple[str,...]
    trace_reference: str
    package_digest: str=''
    def __post_init__(self):
        for name in ('package_id','staging_governance_finalization_reference','staging_entry_review_reference','pre_staging_package_reference','activation_control_plane_reference','activation_decision_reference','readiness_assurance_reference','evidence_governance_reference','trace_reference'):
            v=_n(getattr(self,name))
            if not v or any(x in v.lower() for x in ('secret','password','api_key','bearer ')): raise ValueError(f'invalid {name}')
            object.__setattr__(self,name,v)
        object.__setattr__(self,'control_findings',tuple(_n(x) for x in self.control_findings)); object.__setattr__(self,'boundary_assertions',tuple(_n(x) for x in self.boundary_assertions))
        d=self.canonical_digest()
        if self.package_digest and self.package_digest!=d: raise ValueError('package digest mismatch')
        object.__setattr__(self,'package_digest',d)
    def payload(self): return {k:getattr(self,k) for k in ('package_id','staging_governance_finalization_reference','staging_entry_review_reference','pre_staging_package_reference','activation_control_plane_reference','activation_decision_reference','readiness_assurance_reference','evidence_governance_reference','control_findings','boundary_assertions','trace_reference')} | {'staging_activation':'PROHIBITED','runtime_activation':'PROHIBITED','runtime_admission':'PROHIBITED','execution':False,'deployment':'PROHIBITED'}
    def canonical_digest(self): return hashlib.sha256(json.dumps(self.payload(),ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    @staticmethod
    def evaluate(*,references:tuple[str,...],findings:tuple[str,...]=(),assertions:tuple[str,...]=()):
        refs=tuple(_n(x) for x in references)
        if not refs or any(not x for x in refs) or any(k in x.upper() for x in refs for k in ('BLOCKED','DIGEST_MISMATCH','TRACE_FAILURE','BROKEN_LINEAGE')): return StagingControlOutcome.STAGING_CONTROL_BLOCKED
        if any(k in x.upper() for x in refs for k in ('INVALID','CONTRADICTION')): return StagingControlOutcome.STAGING_CONTROL_NOT_READY
        if any('UNKNOWN' in x.upper() for x in refs): return StagingControlOutcome.UNKNOWN
        allowed={'STAGING_ACTIVATION=PROHIBITED','RUNTIME_ACTIVATION=PROHIBITED','RUNTIME_ADMISSION=PROHIBITED','EXECUTION=FALSE','DEPLOYMENT=PROHIBITED'}
        if any(_n(x).upper() not in allowed for x in assertions): return StagingControlOutcome.STAGING_CONTROL_NOT_READY
        return StagingControlOutcome.STAGING_CONTROL_READY_WITH_WARNINGS if findings else StagingControlOutcome.STAGING_CONTROL_READY
