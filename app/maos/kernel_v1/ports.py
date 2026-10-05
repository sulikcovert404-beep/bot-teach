"""Structural ports only; concrete adapters and I/O are explicitly out of scope."""

from datetime import datetime
from typing import Protocol

from app.maos.kernel_v1.contracts import EnvelopeValidationContext, EnvelopeValidationResult
from app.maos.kernel_v1.evidence import EvidenceEntry, EvidenceHistory
from app.maos.kernel_v1.models import AgentRecord, TaskEnvelopeV1
from app.maos.kernel_v1.tenant import AuthenticatedPrincipal, TenantAuthorizationContext


class TenantAuthorityResolver(Protocol):
    def resolve(
        self,
        principal: AuthenticatedPrincipal,
        requested_tenant_id: str,
        purpose: str,
        *,
        at: datetime,
    ) -> TenantAuthorizationContext | None:
        """Resolve authoritative membership; requested tenant is a selector only."""


class CommanderControlPlanePort(Protocol):
    def create_task(self, task_ref: str) -> str: ...

    def decide(self, task_id: str, decision_ref: str) -> str: ...


class SchedulerPort(Protocol):
    def plan(self, task: TaskEnvelopeV1) -> str: ...


class PolicyEnginePort(Protocol):
    def validate_task(self, task: TaskEnvelopeV1, context: EnvelopeValidationContext) -> EnvelopeValidationResult: ...


class AgentRegistryPort(Protocol):
    def get_agent(self, logical_agent_id: str) -> AgentRecord | None: ...


class AgentRuntimePort(Protocol):
    def execute(self, task: TaskEnvelopeV1, agent: AgentRecord) -> str:
        """Return a result reference; effectful execution requires a separate grant."""


class AIGatewayPort(Protocol):
    def request(self, provider_policy_ref: str, request_ref: str) -> str:
        """Provider-neutral gateway boundary; no provider SDK is exposed to the kernel."""


class ToolBrokerPort(Protocol):
    def invoke(self, task_id: str, grant_ref: str, operation_ref: str) -> str:
        """Revalidate grants at call time; implementation lives outside this package."""


class EvidenceStorePort(Protocol):
    def append(self, entry: EvidenceEntry) -> EvidenceHistory: ...

    def get(self, evidence_id: str, tenant_context: TenantAuthorizationContext) -> EvidenceEntry | None: ...
