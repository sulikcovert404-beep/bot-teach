"""Pure health-state transitions; health does not grant capabilities."""

from datetime import datetime

from app.maos.kernel_v1.models import AgentHealth, AgentRecord


class AgentHealthTransitionRejected(ValueError):
    pass


_HEALTH_TRANSITIONS = {
    AgentHealth.HEALTHY: {AgentHealth.DEGRADED, AgentHealth.BLOCKED, AgentHealth.QUARANTINED},
    AgentHealth.DEGRADED: {AgentHealth.BLOCKED, AgentHealth.QUARANTINED, AgentHealth.RECOVERING},
    AgentHealth.BLOCKED: {AgentHealth.QUARANTINED, AgentHealth.RECOVERING},
    AgentHealth.QUARANTINED: {AgentHealth.RECOVERING},
    AgentHealth.RECOVERING: {AgentHealth.HEALTHY, AgentHealth.DEGRADED, AgentHealth.QUARANTINED},
}


def transition_agent_health(
    record: AgentRecord,
    next_state: AgentHealth,
    *,
    evidence_ref: str,
    policy_version: str,
    occurred_at: datetime,
    authorized_by_health_policy: bool,
    integrity_clearance: bool = False,
) -> AgentRecord:
    """Create a versioned health projection only from policy-qualified evidence."""
    if not authorized_by_health_policy:
        raise AgentHealthTransitionRejected("agents cannot self-update canonical health state")
    if next_state not in _HEALTH_TRANSITIONS[record.health_state]:
        raise AgentHealthTransitionRejected("invalid agent health transition")
    if record.health_state is AgentHealth.QUARANTINED and not integrity_clearance:
        raise AgentHealthTransitionRejected("quarantine recovery requires explicit integrity clearance")
    if not evidence_ref.strip() or not policy_version.strip():
        raise AgentHealthTransitionRejected("health transition requires evidence and policy version")
    if occurred_at.tzinfo is None or occurred_at < record.updated_at:
        raise AgentHealthTransitionRejected("health transition time must be aware and monotonic")
    return AgentRecord(
        logical_agent_id=record.logical_agent_id,
        role=record.role,
        capabilities=record.capabilities,
        input_schema_refs=record.input_schema_refs,
        output_schema_refs=record.output_schema_refs,
        policy_version=policy_version,
        provider_policy_ref=record.provider_policy_ref,
        health_state=next_state,
        health_evidence_ref=evidence_ref,
        updated_at=occurred_at,
        version=record.version + 1,
    )
