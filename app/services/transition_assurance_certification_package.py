"""Immutable transition assurance and certification evidence."""
from dataclasses import dataclass
from enum import Enum
from typing import Tuple
class TransitionCertificationOutcome(str,Enum):
 TRANSITION_CERTIFIED="TRANSITION_CERTIFIED"; TRANSITION_CERTIFIED_WITH_WARNINGS="TRANSITION_CERTIFIED_WITH_WARNINGS"; TRANSITION_NOT_CERTIFIED="TRANSITION_NOT_CERTIFIED"; TRANSITION_BLOCKED="TRANSITION_BLOCKED"; UNKNOWN="UNKNOWN"
@dataclass(frozen=True)
class TransitionAssuranceCertificationPackage:
 package_id:str; planning_reference:str; governance_reference:str; completeness_findings:Tuple[str,...]; integrity_findings:Tuple[str,...]; boundary_findings:Tuple[str,...]; risk_model:Tuple[str,...]; unresolved_risks:Tuple[str,...]; escalation_readiness:Tuple[str,...]; rollback_semantics:Tuple[str,...]; recovery_boundary:Tuple[str,...]; ownership_transfer:Tuple[str,...]; responsibility_consistency:Tuple[str,...]; certification_record:str; trace_reference:str; package_digest:str; transition_assurance_only:bool=True; execution:bool=False; certification_is_execution_permission:bool=False
 def outcome(self)->TransitionCertificationOutcome:
  if not all((self.package_id,self.planning_reference,self.governance_reference,self.trace_reference,self.package_digest)): return TransitionCertificationOutcome.TRANSITION_BLOCKED
  if not self.transition_assurance_only or self.execution or self.certification_is_execution_permission: return TransitionCertificationOutcome.TRANSITION_NOT_CERTIFIED
  groups=(self.completeness_findings,self.integrity_findings,self.boundary_findings,self.risk_model,self.escalation_readiness,self.rollback_semantics,self.recovery_boundary,self.ownership_transfer,self.responsibility_consistency,self.certification_record)
  if any(not x for x in groups): return TransitionCertificationOutcome.TRANSITION_NOT_CERTIFIED
  return TransitionCertificationOutcome.TRANSITION_CERTIFIED_WITH_WARNINGS if self.unresolved_risks else TransitionCertificationOutcome.TRANSITION_CERTIFIED
