# GateMAOS-A12T — Tenant Authority Boundary Design Freeze

**Mode:** read-only source audit
**Source binding:** `e536fdd34854b6f9f4255c96dcb430d160b08d54` (`codex/gate731-target`)
**Worktree:** `C:/Users/IT/.codex/worktrees/maos-a12f/bot telegram teacher`
**Working tree before report:** clean
**Runtime/database/staging:** not accessed
**Code, migration, policy, and configuration mutations:** none; this file is the requested audit artifact.

## Finding

The canonical tenant authority source is the server-side `UserTenantMembership` relation, resolved by `public.resolve_tenant(integer)` and adapted by `app.security.tenant_resolver.resolve_tenant`. Its contract is exactly one row where `status = 'ACTIVE'` and `revoked_at IS NULL`; zero or multiple rows return SQL `NULL`, which the request adapter denies. This is the strongest canonical resolver present in the source.

The source tree is not yet uniformly behind that boundary. Legacy `SchoolAdminMembership` and `TeacherProfile` checks still authorize some routes, and several role-protected routes query tenant-owned records directly or derive `app.tenant_id` from a classroom before a shared canonical tenant-context dependency. The current RLS GUC is a row filter input, not proof of principal identity. The MAOS-specific `maos.current_tenant()` re-resolves membership against two GUCs, but `maos.set_principal_context(integer)` accepts a user ID argument; the application must bind that argument to a freshly authenticated principal before invoking it. No route currently wires the separately qualified Principal Authority Snapshot into tenant authorization.

**Design freeze:** for ordinary `STUDENT`, `TEACHER`, and `SCHOOL_ADMIN` principals, derive one current tenant only from exactly one active, non-revoked `UserTenantMembership` for the authenticated canonical user ID. Never select among multiple rows. `SUPER_ADMIN` with no ordinary membership receives no implicit tenant; tenant access must be an explicitly scoped operation under separately authorized policy, and a missing tenant must remain absent rather than becoming a wildcard or fabricated tenant.

## Evidence and path inventory

| Mechanism | Source evidence | Classification and observation |
|---|---|---|
| Canonical membership model | `app/db/models.py:67-92` | **Authoritative model.** FK to `users` and `school_tenants`; statuses `ACTIVE/REVOKED/SUSPENDED`; revocation timestamp. Unique `(user_id, tenant_id)` permits multiple tenant rows per user by design. It does not itself enforce one active tenant per user. |
| Canonical DB resolver | `migrations/versions/20261003_0024_canonical_tenant_context.py:39-73` | **Authoritative resolver.** `SECURITY DEFINER`, `STABLE`, fixed `search_path=pg_catalog`, fully qualified relation. Counts active, non-revoked rows and returns `NULL` unless count is exactly one. Public execute revoked; conditional execute grant only to `app_runtime`; no direct table grant in this migration. |
| Python resolver | `app/security/tenant_resolver.py:21-46` | **Adapter / test fallback.** PostgreSQL calls `resolve_tenant(:user_id)`. SQLite fallback applies the same status/revocation predicate, limits to two, and differentiates ambiguous membership. PostgreSQL's SQL `NULL` intentionally collapses zero and multiple into generic `TenantResolutionError`; both deny. Other database exceptions propagate and are not converted to tenant scope. |
| Request tenant context | `app/security/tenant_context.py:15-49` | **Canonical propagation path.** `TenantContext` currently holds only `user_id` and `tenant_id`. `establish_tenant_context` begins a transaction if needed, resolves and sets `app.tenant_id` on that session; resolver/value errors rollback and return HTTP 403. Dependency authenticates with `require_roles`, converts subject to integer, then calls this path. It is not a typed authority snapshot and does not include membership/version evidence. |
| Transaction-local GUC | `app/db/base.py:24-42` | **Propagation only.** Validates an opaque identifier, requires an active transaction, uses a bound parameter and `set_config('app.tenant_id', ..., true)` so it is transaction local. The setter accepts any syntactically valid tenant ID and does not resolve membership; callers must establish authority first. |
| Legacy school-admin binding | `app/db/models.py:1697-1710`; `app/security/tenant_scope.py:16-22` | **Legacy / divergent authority.** Separate table and lookup path. `enforce_tenant` authorizes a SCHOOL_ADMIN against this relation rather than `UserTenantMembership`. A row in this legacy table can disagree with, or exist without, canonical membership. |
| Legacy teacher binding | `app/db/models.py:1712-1724`; `app/security/tenant_scope.py:23-25`; `app/security/teacher_scope.py:24-45` | **Legacy / derived scope.** `TeacherProfile` supplies tenant ownership and class IDs without checking canonical membership/revocation. It cannot override or mint canonical authority. |
| Admin query routes | `app/api/routes/admin.py:100-160` | **Unsafe / duplicate.** Six admin GET routes accept `tenant_id` query parameters and use legacy `enforce_tenant`; SUPER_ADMIN passes a requested tenant through without membership resolution. An omitted tenant can result in an unscoped query; some routes set GUC only if scope is truthy, and several read tables not protected by the selected RLS policies. |
| Admin scope helper | `app/security/admin_scope.py:6-25`; `tests/test_admin_scope.py:6-27` | **Unwired policy helper.** It compares an already supplied tenant scope; SUPER_ADMIN may request any tenant or none, and `require_scope` returns `"*"` when both tenant values are absent. No application call site was found. It must not be treated as an authority source. |
| Student assignment context | `app/api/routes/student.py:50-69` and route dependencies at `:53-55` | **Canonical path for covered assignment handlers.** Uses `tenant_context_for("STUDENT")`; exam helper also calls the shared resolver before assignment lookup. Audit did not establish that every student route uses this context. |
| Teacher submission context | `app/api/routes/teacher.py:43` and review/list handlers; direct result route at `:544-566` | **Mixed.** Submission operations use canonical dependency. `/exam-results` separately resolves and sets GUC, then joins legacy `TeacherProfile`; other teacher routes use role checks and legacy profile/classroom relationships without canonical context. |
| Exam intelligence | `app/api/routes/exams.py:295-320` | **Canonical lookup, partial propagation.** Calls `resolve_tenant` and filters by returned tenant, but this route does not call `set_tenant_context` in the inspected handler. It uses JWT-derived role/subject dependency rather than the Principal Authority Snapshot. |
| Source search | `app/api/routes/sources.py:67-99` | **Unsafe context derivation.** `classroom_id` is client-supplied; the handler loads a classroom, authorizes through `TeacherProfile` or `ClassMembership`, then sets GUC from that classroom. This is a distinct selector-to-context path and lacks canonical `UserTenantMembership` resolution in the handler. `POST /sources` has only role dependency and no tenant context in the inspected route. |
| Enterprise report | `app/api/routes/enterprise_success.py:172-190` | **Presentation/demo selector.** `tenant_id` is a query parameter defaulting to `sch-helli-01` and is returned with static report content; no canonical resolution is performed in this handler. If this becomes tenant data access, it needs the canonical boundary first. |
| Tenant membership lifecycle | `app/api/routes/tenant_memberships.py:26-151`; `app/services/tenant_membership.py:1-125`; migration `20261003_0025_tenant_membership_provisioning.py` | **Canonical mutation API, distinct from tenant authorization.** Actor is derived from JWT subject/role and database functions recheck stored actor/target roles; provision/revoke/bootstrap operate on `UserTenantMembership`. The reader audit did not find route-level Principal Authority Snapshot integration. This gate does not authorize or alter these writers. |
| Test identity provisioning | `app/api/routes/admin.py:57-92`; `app/services/test_identity_provisioning.py:60-250` | **Alternate legacy writer.** SUPER_ADMIN-only endpoint provisions test identities. For TEACHER it creates `TeacherProfile`; for SCHOOL_ADMIN it creates `SchoolAdminMembership`; it does not create canonical `UserTenantMembership`. Resulting identities may therefore pass legacy route checks but fail canonical resolution. Keep this test-only path from silently defining production authority. |
| Standard JWT principal | `app/security/principal.py:13-30`; `app/security/authority_snapshot.py:63-140` | **Authentication input / separately qualified fresh snapshot.** Current route principal uses JWT `sub` and role. A12F's `PrincipalAuthoritySnapshot` refetches current user ID, stored role, and A11 lifecycle state; it explicitly contains no tenant and has no call sites in `app/`. JWT role/any tenant claim is not current membership authority. |
| MAOS tenant context and RLS | `migrations/versions/20261006_0034_maos_durable_foundation.py:143-175, 310-329` | **MAOS propagation plus revalidation.** `maos.set_principal_context(user_id)` calls `public.resolve_tenant`, then sets transaction-local principal and tenant GUCs. `maos.current_tenant()` requires both GUCs and re-resolves, returning NULL if the tenant no longer matches. MAOS RLS policies use `maos.current_tenant()`. The supplied user ID is still an input to the SECURITY DEFINER setter; authenticated-subject binding must be enforced above it. |
| Existing public RLS | `migrations/versions/20260910_0016_selected_tenant_rls.py:14-35`; `migrations/versions/20260912_0021_exam_persistence.py:80-87`; `migrations/versions/20261003_0028_submission_revision_expand.py:245-249` | **Row isolation only.** FORCE RLS policies compare row `tenant_id` to `current_setting('app.tenant_id', true)`. Missing GUC yields no matching tenant rows; setting it does not prove who the caller is or whether the user belongs to that tenant. |
| Kernel value objects | `app/maos/kernel_v1/tenant.py:1-29`; `app/maos/kernel_v1/ports.py:12-18` | **Domain contract only.** `TenantAuthorizationContext` is typed but constructed from supplied identifiers and metadata; `TenantAuthorityResolver` is a protocol. No concrete resolver is wired to the canonical membership function in current app call sites. |

## Canonical snapshot V1 boundary

Freeze a future immutable `TenantAuthoritySnapshotV1` as a *decision input*, not a grant or a client-selected tenant. Minimal fields:

- authenticated canonical `principal_id` (the same identity reference used by the Principal Authority Snapshot);
- `tenant_id` from the unique canonical membership;
- canonical `membership_id` as authority reference;
- membership state and revocation evidence observed during resolution (at minimum `ACTIVE`, `revoked_at IS NULL`); add a monotonic membership version only if one is introduced by a separately approved schema gate;
- resolution outcome/evidence category (`RESOLVED_UNIQUE`, `MISSING`, `AMBIGUOUS`, `INACTIVE`, `UNAVAILABLE`), with no secret, token, or request payload.

Resolution order for a future sensitive operation:

1. Authenticate token cryptographically and take only its subject as the lookup key; obtain fresh current role and lifecycle using the already-qualified Principal Authority Snapshot mechanism.
2. Require a canonical decimal user ID and a principal snapshot allowed for the requested operation. Keep principal lifecycle (`UNRECONCILED/ACTIVE/SUSPENDED/DISABLED`) separate from tenant membership state.
3. For ordinary tenant-scoped roles, query only the canonical DB-owned resolver. It must distinguish or safely collapse zero/multiple into denial, never choose a row by order, `min`, newest timestamp, or caller preference.
4. Construct the tenant snapshot from the resolver result and canonical membership evidence. Do not accept caller tenant ID, request header/query/body, standard JWT tenant claim, preview token claim, or GUC as a source of authority.
5. Before a sensitive decision, re-resolve within the decision's transaction so revocation or membership changes invalidate stale state. Avoid caching authority across requests or long-lived operations. Bind the returned tenant and principal to the same transaction and DB session.
6. Only after successful resolution, set the tenant context transaction-locally. For existing public application RLS, set `app.tenant_id`; for MAOS RLS, use a future authenticated adapter to bind the Principal Snapshot's ID to `maos.set_principal_context`. The GUC is the RLS filter context, not authorization.
7. Let RLS enforce row isolation as defense in depth. Missing, malformed, mismatched, or stale context must deny/return no rows. Never weaken RLS or bypass it to discover tenant.
8. For `SUPER_ADMIN`, do not require or synthesize an ordinary membership. A separately authorized operation may explicitly name a target tenant; server policy must validate that target against the operation and then provide scoped access. An absent tenant means no tenant-scoped operation, never `*` or global access by default.

## Failure and stale-state rules

| Condition | V1 result |
|---|---|
| Missing/invalid authenticated principal, no current user, noncanonical stored role | Deny before tenant lookup. |
| Principal lifecycle unavailable, `UNRECONCILED`, `SUSPENDED`, or `DISABLED` where operation requires active principal | Deny; tenant membership cannot override lifecycle. |
| Zero active, non-revoked canonical memberships | Deny `MISSING`; do not fall back to profile/class membership or client selector. |
| More than one active, non-revoked canonical membership | Deny `AMBIGUOUS`; never choose first/most recent. |
| Membership revoked, suspended, or has `revoked_at` | Excluded from eligible rows; deny if no unique eligible row remains. |
| Resolver/database unavailable or malformed result | Deny; no legacy fallback or cache fallback. |
| Tenant snapshot, principal snapshot, transaction identity, or RLS context mismatch | Deny and rollback. |
| SUPER_ADMIN has no ordinary membership | Preserve no-tenant state. Require explicit operation-scoped target authorization; never create implicit tenant context. |

## Legacy divergence and risks

1. `tenant_scope.enforce_tenant` and several teacher paths use `SchoolAdminMembership`/`TeacherProfile`; they do not prove canonical membership. This creates parallel, potentially contradictory authority.
2. Admin endpoints accept `tenant_id` directly. School-admin checks use legacy table; SUPER_ADMIN requests pass through. Omitted target may leave queries global. `admin_scope.require_scope` has a wildcard fallback and is not called by app routes.
3. `sources.search` derives GUC from a selected classroom after legacy membership checks; this is not the canonical principal-to-tenant resolver path. Its pre-context classroom lookup also needs explicit proof that the underlying table is safely protected for the deployed role.
4. `public.resolve_tenant` has no user-role/lifecycle condition; it answers membership only. The Principal Authority Snapshot supplies separate current principal facts, but is not wired into the tenant paths at this commit. Keep the two dimensions separate and compose them at a future authorization boundary.
5. Model uniqueness is per `(user_id, tenant_id)`, not one active tenant per user. The DB resolver safely denies multiple rows. The provisioning function serializes by user and rejects a different active tenant, but that writer invariant does not eliminate historical/manual duplicates and must not replace read-time exact-one checks.
6. Legacy test identity provisioning writes legacy profiles/memberships without canonical memberships. This can create identities with divergent authorization behavior; it is an alternate test-identity lifecycle, not a canonical tenant authority path.
7. MAOS `set_principal_context` takes a user ID argument. `current_tenant` re-resolves the tenant for the GUC user but cannot establish that the GUC user equals the authenticated request principal. A trusted adapter must pass only the freshly verified Principal Snapshot identity; do not treat arbitrary direct invocation as an authentication boundary.
8. `role_preview.py` carries `preview_tenant` in a dedicated short-lived token but the module is not wired to app routes. A preview claim remains a preview selector and cannot create ordinary tenant authority; any future preview flow needs its own separately authorized, auditable, read-only boundary.
9. Historical `docs/GATE733A_CANONICAL_TENANT_CONTEXT_FOUNDATION_RESULT.md` records disposable qualification of `public.resolve_tenant`, transaction-local GUC, and selected assignment routes; it explicitly says membership data/provisioning and deployment were not qualified. The current A12T audit therefore treats that as historical test evidence, not proof of live database deployment.

## Dependency graph for implementation (not performed)

```text
authenticated subject
  ├─> PrincipalAuthoritySnapshot (fresh role + lifecycle; no tenant)
  └─> public.resolve_tenant(user_id)
        └─> exactly-one active, non-revoked UserTenantMembership
              └─> TenantAuthoritySnapshotV1 (principal + tenant + membership evidence)
                    └─> operation-specific authorization / explicit SUPER_ADMIN target policy
                          └─> transaction-local context setter
                                └─> RLS row isolation (defense in depth)
```

Legacy `SchoolAdminMembership`, `TeacherProfile`, client selectors, JWT tenant claims, and GUC values are compatibility/derived/propagation inputs only; none may be promoted to the authority node.

## Human decisions required

- Whether ordinary users may ever hold multiple active tenants in a future product. V1 remains deny-on-multiple until a separate explicit tenant-selection policy is approved; a client choice still requires server validation and cannot relax authority.
- Which operations, if any, permit SUPER_ADMIN explicit tenant targeting versus require no tenant context. No wildcard/global semantics are adopted here.
- Which legacy endpoints are retained, retired, or separately gated before tenant boundary implementation. This audit makes no route or compatibility change.
- Whether membership versioning is required for revocation races; no schema field is assumed or authorized.
- Separate governance/production approval is still needed for lifecycle writer/grant work, migration, route wiring, or deployment.

## Verdict

`TENANT_AUTHORITY_DESIGN_FROZEN_WITH_INTEGRATION_BLOCKERS`

Canonical source and fail-closed V1 semantics are resolved from code evidence. Runtime implementation is not qualified because multiple legacy and selector-derived paths remain, principal snapshot is not wired, and no deployment state was inspected. This report authorizes no repair, migration, DB operation, staging access, or deployment.

**Mutations:** documentation artifact only.
**Recommended next action:** issue a separate implementation gate for one typed tenant snapshot/resolution adapter and enumerate route wiring explicitly; require all legacy bypasses to be disabled or proven compatibility-only before any runtime qualification.
