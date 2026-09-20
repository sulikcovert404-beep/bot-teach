from __future__ import annotations

import hashlib
import json
import unicodedata
from dataclasses import dataclass
from enum import StrEnum


class StagingEntryOutcome(StrEnum):
    STAGING_ENTRY_APPROVED='STAGING_ENTRY_APPROVED'; STAGING_ENTRY_APPROVED_WITH_WARNINGS='STAGING_ENTRY_APPROVED_WITH_WARNINGS'; STAGING_ENTRY_NOT_APPROVED='STAGING_ENTRY_NOT_APPROVED'; STAGING_ENTRY_BLOCKED='STAGING_ENTRY_BLOCKED'; UNKNOWN='UNKNOWN'

def _c(v: str) -> str: return unicodedata.normalize('NFC', str(v)).strip()

@dataclass(frozen=True, slots=True)
class RuntimeActivationStagingEntryReview:
    review_id: str
    pre_staging_governance_package_reference: str
    final_readiness_review_reference: str
    activation_decision_reference: str
    staging_validation_assurance_reference: str
    readiness_baseline_freeze_reference: str
    entry_findings: tuple[str, ...]
    boundary_assertions: tuple[str, ...]
    trace_reference: str
    review_digest: str = ''
    def __post_init__(self):
        names=('review_id','pre_staging_governance_package_reference','final_readiness_review_reference','activation_decision_reference','staging_validation_assurance_reference','readiness_baseline_freeze_reference','trace_reference')
        for n in names:
            v=_c(getattr(self,n))
            if not v or any(x in v.lower() for x in ('secret','password','api_key','bearer ')): raise ValueError(f'invalid {n}')
            object.__setattr__(self,n,v)
        object.__setattr__(self,'entry_findings',tuple(_c(x) for x in self.entry_findings)); object.__setattr__(self,'boundary_assertions',tuple(_c(x) for x in self.boundary_assertions))
        d=self.canonical_digest()
        if self.review_digest and self.review_digest!=d: raise ValueError('review digest mismatch')
        object.__setattr__(self,'review_digest',d)
    def payload(self): return {'review_id':self.review_id,'pre_staging_governance_package_reference':self.pre_staging_governance_package_reference,'final_readiness_review_reference':self.final_readiness_review_reference,'activation_decision_reference':self.activation_decision_reference,'staging_validation_assurance_reference':self.staging_validation_assurance_reference,'readiness_baseline_freeze_reference':self.readiness_baseline_freeze_reference,'entry_findings':self.entry_findings,'boundary_assertions':self.boundary_assertions,'trace_reference':self.trace_reference,'staging_entry':'REVIEW_ONLY','staging_execution':'PROHIBITED','runtime_activation':'PROHIBITED','runtime_admission':'PROHIBITED','execution':False}
    def canonical_digest(self): return hashlib.sha256(json.dumps(self.payload(),ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')).hexdigest()
    @staticmethod
    def evaluate(*,references:tuple[str,...],findings:tuple[str,...]=(),assertions:tuple[str,...]=()):
        vals=tuple(_c(x) for x in references)
        if not vals or any(not x for x in vals) or any(k in x.upper() for x in vals for k in ('BLOCKED','DIGEST_MISMATCH','TRACE_FAILURE')): return StagingEntryOutcome.STAGING_ENTRY_BLOCKED
        if any(k in x.upper() for x in vals for k in ('INVALID','CONTRADICTION')): return StagingEntryOutcome.STAGING_ENTRY_NOT_APPROVED
        if any('UNKNOWN' in x.upper() for x in vals): return StagingEntryOutcome.UNKNOWN
        if any(_c(x).upper() not in ('STAGING_ENTRY=REVIEW_ONLY','STAGING_EXECUTION=PROHIBITED','RUNTIME_ACTIVATION=PROHIBITED','RUNTIME_ADMISSION=PROHIBITED','EXECUTION=FALSE') for x in assertions): return StagingEntryOutcome.STAGING_ENTRY_NOT_APPROVED
        return StagingEntryOutcome.STAGING_ENTRY_APPROVED_WITH_WARNINGS if findings else StagingEntryOutcome.STAGING_ENTRY_APPROVED
