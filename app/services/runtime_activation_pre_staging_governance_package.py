from __future__ import annotations

import hashlib
import json
import unicodedata
from dataclasses import dataclass
from enum import StrEnum


class PreStagingOutcome(StrEnum):
    PRE_STAGING_READY='PRE_STAGING_READY'; PRE_STAGING_READY_WITH_WARNINGS='PRE_STAGING_READY_WITH_WARNINGS'; PRE_STAGING_NOT_READY='PRE_STAGING_NOT_READY'; PRE_STAGING_BLOCKED='PRE_STAGING_BLOCKED'; UNKNOWN='UNKNOWN'

def _c(v: str) -> str: return unicodedata.normalize('NFC', str(v)).strip()

@dataclass(frozen=True, slots=True)
class RuntimeActivationPreStagingGovernancePackage:
    package_id: str
    final_readiness_review_reference: str
    activation_decision_reference: str
    activation_control_plane_reference: str
    governance_closure_reference: str
    readiness_baseline_freeze_reference: str
    staging_validation_framework_reference: str
    staging_evidence_governance_reference: str
    staging_validation_assurance_reference: str
    trace_reference: str
    package_digest: str = ''

    def __post_init__(self) -> None:
        names = ('package_id','final_readiness_review_reference','activation_decision_reference','activation_control_plane_reference','governance_closure_reference','readiness_baseline_freeze_reference','staging_validation_framework_reference','staging_evidence_governance_reference','staging_validation_assurance_reference','trace_reference')
        for name in names:
            value = _c(getattr(self, name))
            if not value or any(token in value.lower() for token in ('secret','password','api_key','bearer ')):
                raise ValueError(f'invalid {name}')
            object.__setattr__(self, name, value)
        digest = self.canonical_digest()
        if self.package_digest and self.package_digest != digest: raise ValueError('package digest mismatch')
        object.__setattr__(self, 'package_digest', digest)

    def payload(self) -> dict[str, object]:
        return {'package_id': self.package_id, 'final_readiness_review_reference': self.final_readiness_review_reference, 'activation_decision_reference': self.activation_decision_reference, 'activation_control_plane_reference': self.activation_control_plane_reference, 'governance_closure_reference': self.governance_closure_reference, 'readiness_baseline_freeze_reference': self.readiness_baseline_freeze_reference, 'staging_validation_framework_reference': self.staging_validation_framework_reference, 'staging_evidence_governance_reference': self.staging_evidence_governance_reference, 'staging_validation_assurance_reference': self.staging_validation_assurance_reference, 'trace_reference': self.trace_reference, 'staging_execution': 'PROHIBITED', 'runtime_activation': 'PROHIBITED', 'runtime_admission': 'PROHIBITED', 'execution': False, 'deployment': 'PROHIBITED'}

    def canonical_digest(self) -> str: return hashlib.sha256(json.dumps(self.payload(), ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()

    @staticmethod
    def evaluate(*, references: tuple[str, ...], findings: tuple[str, ...] = ()) -> PreStagingOutcome:
        values = tuple(_c(x) for x in references)
        if not values or any(not x for x in values) or any(k in x.upper() for x in values for k in ('BLOCKED','DIGEST_MISMATCH','TRACE_FAILURE')): return PreStagingOutcome.PRE_STAGING_BLOCKED
        if any(k in x.upper() for x in values for k in ('INVALID','CONTRADICTION')): return PreStagingOutcome.PRE_STAGING_NOT_READY
        if any('UNKNOWN' in x.upper() for x in values): return PreStagingOutcome.UNKNOWN
        return PreStagingOutcome.PRE_STAGING_READY_WITH_WARNINGS if findings else PreStagingOutcome.PRE_STAGING_READY
