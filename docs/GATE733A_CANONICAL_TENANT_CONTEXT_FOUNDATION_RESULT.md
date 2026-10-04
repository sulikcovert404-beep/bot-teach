# Gate733A — Canonical Tenant Context Foundation

Date: 2026-10-03

## Verdict

`PASS` — `TENANT FOUNDATION READY` for a later separately authorized deployment gate.

Production and staging remain out of scope. This result qualifies the canonical database resolver, request tenant context, and assignment submission HTTP lifecycle only on a disposable PostgreSQL database.

## Lineage reconciliation

- Qualification worktree: `D:/project/ai-teacher-gate731-target`
- Gate732 implementation worktree: same path, branch `codex/gate731-target`
- Base/HEAD: `e4140c4d55a2943c53ecc187a28729663073d48d`
- Gate732N implementation and migration `20260924_0023` existed as uncommitted work in this tree, recorded by its start/result reports. The migration, service and revision tests were retained; no reset, stash, copy, cherry-pick, or commit was performed.
- Gate732R ran against the primary checkout at the same base commit, where the 0023 work was absent. The difference is explained by the separate, dirty Gate732N worktree, not by a different base commit or a database artifact.
- Gate733A added `20261003_0024` on `20260924_0023`. `alembic heads` reports the single head `20261003_0024`.

## Canonical design

- Membership model: existing `UserTenantMembership`, with user and tenant foreign keys, unique `(user_id, tenant_id)`, status constraint `ACTIVE | REVOKED | SUSPENDED`, and existing creation/revocation metadata. The tenant FK targets canonical `school_tenants.tenant_id`; there is no global unique constraint on `user_id`.
- Resolver: `public.resolve_tenant(integer)` returns a tenant only when exactly one membership is `ACTIVE` and has no `revoked_at`; zero or multiple matches return `NULL` for fail-closed handling.
- Function owner: migration identity (`gate732` in the disposable cluster); `SECURITY DEFINER`, `STABLE`, fixed `search_path=pg_catalog`, and fully qualified membership table.
- Runtime grants: `PUBLIC EXECUTE` revoked; `EXECUTE` granted only to existing `app_runtime`. No direct membership-table grant is made.
- Tenant GUC: existing `app.tenant_id`, set transaction-locally through `set_tenant_context`.
- Request dependency: shared `tenant_context_for(...)` authenticates role, resolves the tenant, and sets the GUC using the same cached `get_session` instance used by the endpoint. Student assignment list/detail/resume/submit/feedback and teacher submission list/review use this dependency. Tenant identifiers from request parameters do not select scope.

## Migration qualification

- Revision: `20261003_0024`; parent: `20260924_0023`.
- Fresh chain through head: PASS.
- Empty-database downgrade to `20260924_0023` and rebuild to head: PASS.
- Downgrade after memberships exist: refused; transaction left head and membership rows intact.
- Disposable database and temporary `app_runtime` role removed after qualification. The Gate732 disposable PostgreSQL container remained running and unchanged; cleanup check returned zero matching Gate733 databases and zero `app_runtime` roles.

## Security qualification

- `app_runtime` SUPERUSER: NO
- `app_runtime` BYPASSRLS: NO
- Direct membership SELECT: NO
- Resolver EXECUTE for `app_runtime`: YES
- PUBLIC EXECUTE: NO
- Zero / one / multiple active membership: denied / resolves / denied
- No-context assignment RLS: zero rows
- Tenant A/B RLS: each runtime context saw only its own tenant's row
- The runtime could call the resolver without membership-table access.

## HTTP qualification

Using real JWT role checks, the restricted PostgreSQL role, and the canonical resolver:

- Authorized student: list/detail/submit/feedback PASS.
- Submit replay: PASS; same key and payload replayed.
- Same key with changed payload: HTTP 409.
- New key: revision 2 created.
- Authorized teacher: submission list and exact-revision review PASS.
- Unauthenticated request: HTTP 401.
- Wrong role: HTTP 403.
- A supplied `tenant_id=gate733-b` query parameter did not change the authenticated tenant scope.
- Cross-tenant assignment and cross-user feedback/review attempts: HTTP 404.
- Review feedback was returned only to the owning student.

## Quality and mutations

- Focused suite including the disposable PostgreSQL/HTTP integration: **29 passed, 1 skipped**. The skip is a separate legacy Gate732 test that requires its own port variable; the Gate733 integration test ran and passed.
- `compileall`: PASS.
- `git diff --check`: PASS.
- Ruff on the new tenant dependency, migration, and Gate733 integration test: PASS. The pre-existing modified route files retain broader Ruff debt; this gate did not reformat unrelated code. The Gate732N route edits and Gate733 route integration were reviewed separately from the clean new files.
- Production: NONE. Staging: NONE. Server: NONE. Commit: NONE.
- Only the dedicated local disposable PostgreSQL test database and temporary role were mutated; both were removed. No other project or persistent database was touched.

## Existing Gate732 revision work

`PRESENT` — migration `20260924_0023`, `submission_revisions.py`, and the Gate732 revision tests remain in the target worktree. Their contents were not overwritten or reset. The existing route modules were extended to use the shared Gate733 tenant dependency, then the full submission/review/feedback lifecycle was requalified through HTTP.

## Remaining boundary

The membership table has no production membership records or provisioning workflow qualified by this gate. Requests without exactly one active membership correctly fail closed. Membership provisioning ownership and any staging/production migration or deployment require a separate explicit gate.

**FINAL: TENANT FOUNDATION READY — not deployed**
