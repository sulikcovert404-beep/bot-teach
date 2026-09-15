# Tenant Identity Model Decision

Status: RECOMMENDATION / DESIGN ONLY  
Production mutation: NONE  
Migration: NOT CREATED

## Selected model

Use an authoritative `UserTenantMembership` binding (or the project's equivalent canonical membership model) keyed by `user_id` and `tenant_id`, with explicit status, revocation, timestamps, and uniqueness for active membership. Do not add a single `tenant_id` to `StudentProfile`: the platform supports school/tenant boundaries and may need users to belong to more than one school over time.

The binding is the pre-RLS identity source. It must be readable by a narrowly scoped resolver boundary before tenant-owned queries, must not expose a global dataset to application services, and must be audited on membership changes.

## Tenant ownership rule

- **Student:** active enrollment/membership determines eligible tenant(s) and classroom scope.
- **Teacher:** active teacher membership determines tenant(s); classroom assignment further narrows access.
- **School Admin:** existing active `SchoolAdminMembership` remains authoritative.
- **SUPER_ADMIN:** no implicit global tenant context; tenant-owned operations require an explicit tenant selected by the request and server-validated against an allowed scope.

No role may use a client-supplied tenant as authority.

## Multi-tenant policy

An identity with one active tenant may receive a short-lived server-bound context. An identity with multiple active tenants must select a tenant through an authenticated, server-validated context switch; no silent “first row” choice is allowed. Revocation immediately invalidates new context issuance. Existing context tokens remain bounded by expiry and should be rejected when membership version/revocation is checked at the resolver boundary.

## Auth and JWT impact

The current JWT (`sub`, `role`, `iat`, `exp`) remains valid for compatibility. Do not add a tenant claim until the binding exists and membership validation is implemented. After that gate, a short-lived tenant-bound context claim may be added as a derived hint, but every request must still validate it against the authoritative binding before calling `set_tenant_context`.

## RLS compatibility and first query

The resolver boundary obtains the identity binding, selects/validates one tenant, begins the request transaction, calls `set_tenant_context(..., is_local=true)`, and only then queries Assignment, Exam, ClassMembership/Classroom, Attempt, or Result. Missing, ambiguous, revoked, or mismatched membership fails closed. No global query/post-filter, RLS disable, or BYPASSRLS is permitted.

## Migration impact

Likely schema work is required for a canonical student/teacher identity binding or an equivalent non-tenant resolver view. This is a separate migration design gate requiring AI/team review, disposable PostgreSQL upgrade/downgrade/re-upgrade, backfill/orphan analysis, and explicit production approval. This document creates no migration and changes no runtime behavior.

## Decision requested

Approve `UserTenantMembership` as the authoritative model and define whether enrollment history, multiple active tenants, and context switching are required for the pilot. Until approved and implemented, Exam 0021 application qualification and migration remain blocked; production stays at `20260912_0020`.
