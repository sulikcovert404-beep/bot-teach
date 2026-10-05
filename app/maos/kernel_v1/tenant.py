"""Authenticated identity and tenant authorization value objects."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AuthenticatedPrincipal:
    principal_id: str
    authentication_ref: str

    def __post_init__(self) -> None:
        if not self.principal_id.strip() or not self.authentication_ref.strip():
            raise ValueError("authenticated principal identity is required")


@dataclass(frozen=True, slots=True)
class TenantAuthorizationContext:
    principal_id: str
    tenant_id: str
    purpose: str
    authorization_ref: str
    policy_version: str

    def __post_init__(self) -> None:
        if not all((self.principal_id, self.tenant_id, self.purpose, self.authorization_ref, self.policy_version)):
            raise ValueError("tenant authorization context must be complete")
