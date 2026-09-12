from __future__ import annotations
from dataclasses import dataclass
from enum import StrEnum
import hashlib, json, unicodedata
class ClosureOutcome(StrEnum):
    STAGING_GOVERNANCE_CLOSED='STAGING_GOVERNANCE_CLOSED'; STAGING_GOVERNANCE_CLOSED_WITH_WARNINGS='STAGING_GOVERNANCE_CLOSED_WITH_WARNINGS'; STAGING_GOVERNANCE_OPEN='STAGING_GOVERNANCE_OPEN'; STAGING_GOVERNANCE_BLOCKED='STAGING_GOVERNANCE_BLOCKED'; UNKNOWN='UNKNOWN'
def _n(v:str)->str:return unicodedata.normalize('NFC',str(v)).strip()
@dataclass(frozen=True,slots=True)
class StagingActivationGovernanceClosure:
    closure_id:str; staging_control_package_reference:str; staging_governance_finalization_reference:str; staging_entry_review_reference:str; activation_readiness_assurance_reference:str; activation_control_plane_reference:str; boundary_assertions:tuple[str,...]; closure_findings:tuple[str,...]; trace_reference:str; closure_digest:str=''
    def __post_init__(self):
        for n in ('closure_id','staging_control_package_reference','staging_governance_finalization_reference','staging_entry_review_reference','activation_readiness_assurance_reference','activation_control_plane_reference','trace_reference'):
            v=_n(getattr(self,n))
            if not v or any(x in v.lower() for x in ('secret','password','api_key','bearer ')):raise ValueError(f'invalid {n}')
            object.__setattr__(self,n,v)
        object.__setattr__(self,'boundary_assertions',tuple(_n(x) for x in self.boundary_assertions));object.__setattr__(self,'closure_findings',tuple(_n(x) for x in self.closure_findings));d=self.canonical_digest()
        if self.closure_digest and self.closure_digest!=d:raise ValueError('closure digest mismatch')
        object.__setattr__(self,'closure_digest',d)
    def payload(self):return {k:getattr(self,k) for k in ('closure_id','staging_control_package_reference','staging_governance_finalization_reference','staging_entry_review_reference','activation_readiness_assurance_reference','activation_control_plane_reference','boundary_assertions','closure_findings','trace_reference')}|{'staging_activation':'PROHIBITED','runtime_activation':'PROHIBITED','runtime_admission':'PROHIBITED','execution':False,'deployment':'PROHIBITED'}
    def canonical_digest(self):return hashlib.sha256(json.dumps(self.payload(),ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    @staticmethod
    def evaluate(*,references:tuple[str,...],findings:tuple[str,...]=(),assertions:tuple[str,...]=()):
        r=tuple(_n(x) for x in references)
        if not r or any(not x for x in r) or any(k in x.upper() for x in r for k in ('BLOCKED','DIGEST_MISMATCH','TRACE_FAILURE','BROKEN_LINEAGE','CONFLICT')):return ClosureOutcome.STAGING_GOVERNANCE_BLOCKED
        if any(k in x.upper() for x in r for k in ('INVALID','OPEN','INCONSISTENT')):return ClosureOutcome.STAGING_GOVERNANCE_OPEN
        if any('UNKNOWN' in x.upper() for x in r):return ClosureOutcome.UNKNOWN
        allowed={'STAGING_ACTIVATION=PROHIBITED','RUNTIME_ACTIVATION=PROHIBITED','RUNTIME_ADMISSION=PROHIBITED','EXECUTION=FALSE','DEPLOYMENT=PROHIBITED'}
        if any(_n(x).upper() not in allowed for x in assertions):return ClosureOutcome.STAGING_GOVERNANCE_OPEN
        return ClosureOutcome.STAGING_GOVERNANCE_CLOSED_WITH_WARNINGS if findings else ClosureOutcome.STAGING_GOVERNANCE_CLOSED
