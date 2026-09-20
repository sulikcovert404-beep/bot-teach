"""Immutable governance contract for staging evidence; collection is external."""
from __future__ import annotations

import hashlib
import json
import unicodedata
from dataclasses import dataclass
from enum import StrEnum


class EvidenceGovernanceOutcome(StrEnum):
    EVIDENCE_GOVERNANCE_READY="EVIDENCE_GOVERNANCE_READY"
    EVIDENCE_GOVERNANCE_READY_WITH_WARNINGS="EVIDENCE_GOVERNANCE_READY_WITH_WARNINGS"
    EVIDENCE_GOVERNANCE_NOT_READY="EVIDENCE_GOVERNANCE_NOT_READY"
    EVIDENCE_GOVERNANCE_BLOCKED="EVIDENCE_GOVERNANCE_BLOCKED"
    UNKNOWN="UNKNOWN"

def _c(v:str)->str:return unicodedata.normalize("NFC",str(v)).strip()

@dataclass(frozen=True, slots=True)
class RuntimeActivationStagingEvidenceGovernance:
    governance_id:str
    staging_validation_framework_reference:str
    final_readiness_review_reference:str
    activation_decision_reference:str
    evidence_requirements:tuple[str,...]
    evidence_ownership:tuple[str,...]
    validation_rules:tuple[str,...]
    trace_reference:str
    governance_digest:str=""
    def __post_init__(self)->None:
        for n in ("governance_id","staging_validation_framework_reference","final_readiness_review_reference","activation_decision_reference","trace_reference"):
            v=_c(getattr(self,n))
            if not v or any(x in v.lower() for x in ("secret","password","api_key","bearer ")): raise ValueError(f"invalid {n}")
            object.__setattr__(self,n,v)
        for n in ("evidence_requirements","evidence_ownership","validation_rules"):
            object.__setattr__(self,n,tuple(_c(x) for x in getattr(self,n)))
        d=self.canonical_digest()
        if self.governance_digest and self.governance_digest!=d: raise ValueError("governance digest mismatch")
        object.__setattr__(self,"governance_digest",d)
    def payload(self)->dict[str,object]:
        return {"governance_id":self.governance_id,"staging_validation_framework_reference":self.staging_validation_framework_reference,"final_readiness_review_reference":self.final_readiness_review_reference,"activation_decision_reference":self.activation_decision_reference,"evidence_requirements":self.evidence_requirements,"evidence_ownership":self.evidence_ownership,"validation_rules":self.validation_rules,"trace_reference":self.trace_reference,"actual_evidence_collection":"PROHIBITED","staging_execution":"PROHIBITED","deployment":"PROHIBITED","runtime_activation":"PROHIBITED","runtime_admission":"PROHIBITED","execution":False}
    def canonical_digest(self)->str:
        return hashlib.sha256(json.dumps(self.payload(),ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    @staticmethod
    def evaluate(*,references:tuple[str,...],requirements:tuple[str,...]=(),ownership:tuple[str,...]=(),rules:tuple[str,...]=())->EvidenceGovernanceOutcome:
        r=tuple(_c(x) for x in references)
        if not r or any(not x for x in r) or any(k in x.upper() for x in r for k in ("BLOCKED","DIGEST_MISMATCH","TRACE_FAILURE")): return EvidenceGovernanceOutcome.EVIDENCE_GOVERNANCE_BLOCKED
        if any(k in x.upper() for x in r for k in ("INVALID","CONTRADICTION")): return EvidenceGovernanceOutcome.EVIDENCE_GOVERNANCE_NOT_READY
        if any("UNKNOWN" in x.upper() for x in r) or not requirements or not ownership or not rules: return EvidenceGovernanceOutcome.UNKNOWN
        if any("WARNING" in x.upper() for x in requirements+ownership+rules): return EvidenceGovernanceOutcome.EVIDENCE_GOVERNANCE_READY_WITH_WARNINGS
        return EvidenceGovernanceOutcome.EVIDENCE_GOVERNANCE_READY
