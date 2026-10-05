"""Fail-closed risk authority decisions over trusted policy inputs."""

from dataclasses import dataclass

from app.maos.kernel_v1.models import RiskClass

_RISK_ORDER = {
    RiskClass.LOW: 0,
    RiskClass.MEDIUM: 1,
    RiskClass.HIGH: 2,
    RiskClass.CRITICAL: 3,
}


@dataclass(frozen=True, slots=True)
class RiskAssessment:
    effective_risk: RiskClass
    decision_gate_required: bool
    authorized_to_proceed: bool
    rationale_ref: str


def assess_risk(
    policy_classification: RiskClass | None,
    agent_recommendation: RiskClass | None,
    *,
    decision_gate_approved: bool,
    rationale_ref: str,
) -> RiskAssessment:
    """Take the more restrictive classification; agent input cannot downgrade risk."""
    if not rationale_ref.strip() or policy_classification is None:
        return RiskAssessment(RiskClass.CRITICAL, True, False, rationale_ref or "missing-policy-evidence")
    candidates = [policy_classification]
    if agent_recommendation is not None:
        candidates.append(agent_recommendation)
    effective = max(candidates, key=_RISK_ORDER.__getitem__)
    gate_required = _RISK_ORDER[effective] >= _RISK_ORDER[RiskClass.HIGH]
    return RiskAssessment(effective, gate_required, (not gate_required) or decision_gate_approved, rationale_ref)
