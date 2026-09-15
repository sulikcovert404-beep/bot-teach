# Identity → Tenant Resolution Design

Status: PARTIAL / DESIGN ONLY  
Production mutation: NONE  
Migration impact: UNDECIDED (separate gate required)

## Current flow and dependency cycle

Current JWTs contain `sub`, `iat`, `exp`, and optional `role`; they do not contain a tenant scope. `StudentProfile` has no tenant column. Student membership reaches a tenant through `ClassMembership → Classroom.tenant_id`, while `classrooms` and `assignments` are tenant-owned and protected by FORCE RLS. Therefore the current flow is:

```text
JWT(subject)
  → Assignment/ClassMembership lookup
  → tenant discovery
```

but RLS requires:

```text
tenant discovery
  → set_tenant_context()
  → Assignment/ClassMembership lookup
```

This cycle cannot be solved by trusting a client parameter, disabling RLS, or granting BYPASSRLS.

## Options

### Option A — Identity membership resolver

Resolve `subject → tenant(s)` from an authoritative identity-to-tenant source before tenant RLS. The current schema has no non-tenant identity binding for students; `StudentProfile` alone is insufficient. A dedicated resolver table/view or an approved resolver boundary would be required, with explicit handling for users belonging to multiple tenants.

### Option B — Server-issued tenant-bound token

Add a tenant scope to JWT only after the server validates membership during authentication. This is safe only if authentication can consult the authoritative resolver from Option A; adding a claim without that source merely moves the trust problem.

### Option C — Explicit server-validated context

Accept a requested tenant only for roles with an authoritative server-side ownership check (for example, `SUPER_ADMIN`). Ordinary students/teachers must never supply an unverified tenant. This option cannot bootstrap Student Exam access while the resolver source is missing.

## Recommended decision

Adopt Option A as the canonical source, then optionally issue a short-lived tenant-bound token (Option B) to avoid repeated resolution. Define a unique active tenant binding or an explicit tenant-selection flow for multi-tenant identities. The resolver must be readable before tenant-scoped queries without exposing cross-tenant rows to application services; its access boundary and audit behavior require a dedicated security/schema gate.

## First tenant-owned queries

For the Exam path, these are tenant-dependent: Assignment lookup, Exam lookup, ClassMembership/Classroom authorization, Attempt reads/writes, and Result reads/writes. The resolver must complete before all of them. After resolution, begin a transaction, set `app.tenant_id` with `is_local=true`, and call the service.

## Failure and security rules

- no binding, revoked membership, ambiguous tenant, invalid token, or context failure → fail closed;
- never global-search then post-filter;
- never trust client tenant IDs or unvalidated JWT claims;
- never disable FORCE RLS or grant BYPASSRLS;
- pool release must clear context through transaction end.

## Migration and rollout impact

No migration or token change is authorized by this design gate. A future implementation must specify the authoritative binding schema, multi-tenant semantics, token compatibility/expiry, backfill, rollback, and disposable PostgreSQL qualification before production consideration.

## Commander Decision Required

Choose the authoritative identity-to-tenant source and multi-tenant policy. Until that decision is made, Exam 0021 application qualification and production migration remain blocked; production stays at `20260912_0020`.
