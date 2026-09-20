from app.services.transition_assurance_certification_package import *


def make(**o):
 d={"package_id": "p","planning_reference": "plan","governance_reference": "gov","completeness_findings": ("ok",),"integrity_findings": ("ok",),"boundary_findings": ("ok",),"risk_model": ("low",),"unresolved_risks": (),"escalation_readiness": ("ready",),"rollback_semantics": ("defined",),"recovery_boundary": ("bounded",),"ownership_transfer": ("defined",),"responsibility_consistency": ("ok",),"certification_record": "record","trace_reference": "trace","package_digest": "digest"}; d.update(o); return TransitionAssuranceCertificationPackage(**d)
def test_certified(): assert make().outcome() is TransitionCertificationOutcome.TRANSITION_CERTIFIED
def test_warning_blocked(): assert make(unresolved_risks=("open",)).outcome() is TransitionCertificationOutcome.TRANSITION_CERTIFIED_WITH_WARNINGS; assert make(package_digest="").outcome() is TransitionCertificationOutcome.TRANSITION_BLOCKED
def test_guard(): assert make(certification_is_execution_permission=True).outcome() is TransitionCertificationOutcome.TRANSITION_NOT_CERTIFIED
