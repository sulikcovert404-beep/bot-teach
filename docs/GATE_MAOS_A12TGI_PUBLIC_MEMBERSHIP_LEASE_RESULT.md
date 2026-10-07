# Gate MAOS-A12TGI — Public Membership Lease Qualification

## Finding

**Candidate migration 20261007_0036 passes local PostgreSQL 16 qualification after the A12TGIR correction.** A12TGIP review found a principal-context binding defect: clearing both active and validated principal markers to empty strings let the lease predicate accept the remaining lease marker and lock. A12TGIR dynamically reproduced the issue on the unreleased candidate, then corrected the predicate and extended the harness. The corrected predicate binds active principal, validated principal, lease principal, and held advisory-lock identity, and requires all tenant context markers to be present and equal.

**Scope verdict: `PASS_LOCAL_CANDIDATE_ONLY`.** This is not a deployment or application-integration acceptance. There was no route wiring, commit, push, CI run, or connection to staging or production. Runtime callers must be wired in a separately authorized gate to invoke acquisition and validation as two separate SQL statements on the same physical connection and transaction.

## Evidence

### Pinned baseline and reproduction

- Isolated worktree: `C:\Users\IT\.codex\worktrees\maos-a12tgi\bot telegram teacher`
- Baseline `HEAD`: `a2e3b3143b1d8e4c15c457e405fe7e349a973d3f`.
- The Commander-specified remote branch was read-only checked at the start of this task and matched the same SHA.
- Alembic topology at the baseline reported one head, `20261006_0035`.
- The disposable PostgreSQL 16.15 instance was replayed to explicit revision `20261004_0032`, then through explicit targets `20261004_0033`, `20261006_0034`, and `20261006_0035`. The exact starting database revision for the candidate was verified as `20261006_0035`.
- Before applying the candidate, a two-connection READ COMMITTED race used the canonical `public.revoke_tenant_membership` operation. The protected connection first resolved `a12tgi-tenant` and populated the legacy `app.tenant_id` GUC. The revoke transaction then committed. A new resolver statement returned `NULL`, while the old GUC still exposed one exam row (`rows_visible_under_old_guc_after_commit = 1`). This reproduces the pre-fix stale-context defect.

### Candidate implementation

- Candidate revision: `20261007_0036`, parent `20261006_0035`.
- Pre-repair file SHA256: `1A8EEB066CE58F93D15AE608645E01F6A1CBB01B4CB23E630A8301B424935580`.
- A12TGIR corrected file SHA256: `0894DDAEA5AB8E1CCF67C93DFD8868A4E9AAA83F4B83641865CA918C0C397D7D`.
- The migration creates three narrowly scoped SECURITY DEFINER functions owned by `tenant_lease_owner`, a NOLOGIN/NOSUPERUSER/NOBYPASSRLS role:
  - `acquire_public_tenant_membership_lease(integer,text)` — rejects non-READ-COMMITTED transactions, clears old tenant authority context, and obtains the shared transaction advisory lock.
  - `validate_public_tenant_membership_lease(integer,text)` — verifies that same transaction holds the expected shared lock and resolves the user's active membership in a separate statement after acquisition.
  - `has_public_tenant_membership_lease(text)` — fails closed unless the active `app.user_id`, validated principal ID, and lease marker's user ID are valid, positive, and equal; the transaction holds that same user's shared advisory lock; and the active, validated, and lease tenant markers are present and equal to the policy tenant.
- The key is the existing canonical writer key: `hashtextextended('tenant-membership-user:' || user_id::text, 0)`. PostgreSQL 16 `pg_locks` decoding was experimentally checked against this exact 64-bit key.
- All 12 existing `public` tenant RLS policies now require both tenant-context equality and `has_public_tenant_membership_lease(tenant_id::text)` for `USING` and `WITH CHECK`.
- `app_runtime` receives EXECUTE on the three functions, but no direct SELECT/INSERT/UPDATE/DELETE privilege on `user_tenant_memberships`. PUBLIC EXECUTE was revoked. The owner role can call the existing database-owned `resolve_tenant` function and has no direct membership-table grant.
- Source review found the baseline's canonical membership write paths in `20261003_0025_tenant_membership_provisioning.py`: `bootstrap_school_tenant`, `provision_tenant_membership`, and `revoke_tenant_membership`. Each already takes the matching exclusive transaction advisory lock before its membership write. The route/service path uses the provision and revoke database functions; no application-side membership DML was found.
- No canonical suspend/status-update, reassignment, or delete operation was present at revision 0035. Those paths were not invented or modified. A suspended fixture was denied by the resolver/lease check; any future mutation API for these operations must take the same exclusive per-principal lock.

### Disposable PostgreSQL qualification

The qualification harness is `tests/gate_maos_a12tgi_membership_lease_qualification.py`. It refuses non-loopback database URLs or database names without `a12tgi`. Test-only privileges and memberships are reverted, and the uniquely generated user/tenant fixtures are removed by the harness.

Results on PostgreSQL 16.15:

| Check | Result |
|---|---|
| Candidate upgrade from exact 0035 | PASS |
| Candidate downgrade to exact 0035, restored policy/function state | PASS |
| Candidate re-upgrade after downgrade | PASS |
| Forged `app.tenant_id` / `app.user_id` GUC only, RLS SELECT and INSERT | DENIED |
| Valid lease, RLS SELECT and INSERT | PASS |
| Reused physical connection after transaction commit | PASS; prior lease not retained |
| Wrong user, missing/mismatched tenant context | DENIED |
| REPEATABLE READ | Lease acquisition refused; RLS denied |
| Protected transaction wins before revoke | PASS; canonical revoke waited until protected transaction committed |
| Revoke wins before protected acquisition | PASS; waiting request acquired after commit, fresh resolver returned no membership, RLS denied |
| Canonical provision waits for the principal lease | PASS |
| Mutation rollback | PASS; membership remained active and lock released |
| Ambiguous second active membership | DENIED |
| Suspended membership fixture | DENIED |
| Function owner/ACL and all 12 policy predicates | PASS |
| A12TGIR empty/missing/malformed/non-positive/mismatched principal context and wrong-user lock cases | DENIED; helper false and protected SELECT returns zero rows |
| A12TGIR missing/empty/mismatched tenant markers | DENIED; helper false and protected SELECT returns zero rows |
| Deadlock | None observed in the tested lock orderings |

Focused validation also passed:

- `python -m py_compile migrations/versions/20261007_0036_public_membership_lease.py tests/gate_maos_a12tgi_membership_lease_qualification.py`
- `python -m ruff check migrations/versions/20261007_0036_public_membership_lease.py tests/gate_maos_a12tgi_membership_lease_qualification.py`
- `python -m compileall -q app migrations tests`
- Python 3.12.14 canonical `python scripts/mypy_baseline_gate.py`: `MYPY_BASELINE=579 CURRENT=579 NEW=0 RESOLVED=0 UNCHANGED=579`.
- `git diff --cached --check` (after staging only the three candidate/report files).

The disposable database was explicitly downgraded to 0035 and re-upgraded to 0036 after the correction; both operations passed. It is left at candidate revision 0036 pending final evidence capture. The task-owned PostgreSQL container is stopped after capture; no other Docker container is stopped or changed.

### A12TGIR reproduced defect and correction

- On the pre-repair candidate, a live lease for principal U and tenant T remained accepted after both `app.user_id` and `app.public_membership_lease_validated_user_id` were set to empty strings. The predicate returned true and public RLS returned one row. This reproduced the review finding dynamically before the edit.
- The correction adds explicit positive-integer parsing and equality checks for the active, validated, and lease user IDs, binds the existing shared lock check to that user ID, and requires the active, lease, and validated tenant markers to exist and match the policy tenant.
- The harness now proves denial for missing, empty, malformed, non-positive, or mismatched principal and tenant markers, plus a valid alternate principal marker with the lock held for the wrong user. It checks both the helper result and protected-row visibility, then restores a valid context for subsequent cases.
- The complete PostgreSQL qualification harness passed after the correction, including the prior concurrency, rollback, ACL, policy, and lifecycle cases. Explicit downgrade/re-upgrade also passed.
- No lock namespace, role ACL, policy coverage, or application/runtime source was broadened or changed. Ruff, py_compile, compileall, and the canonical mypy baseline gate passed; the baseline remains at 579 unchanged findings with zero new findings.

## Risk and limits

1. The boundary explicitly excludes a fully compromised shared `app_runtime` role impersonating any valid principal. That role can request a lease for an arbitrary principal; this candidate binds SQL context to its lease and lock but does not authenticate the application principal.
2. No API or route calls these functions yet. Until separately wired, the candidate migration alone does not make the application use the lease protocol. The caller must keep acquisition, validation, and protected RLS work on the same connection and transaction, and must treat `false` as denial.
3. The present migration inventory has no canonical suspend/status-update, reassignment, or delete function. If one is later added, it must acquire the same exclusive transaction lock for the affected principal(s), in a stable order for multi-principal changes.
4. The lock is transaction-scoped and does not preempt a protected request that acquired its lease first. That request can finish its transaction; the mutation waits and commits afterward. Requests waiting behind a committed revoke are denied by the fresh validation statement.
5. Qualification used a fresh, loopback-only PostgreSQL 16 database and a task-owned disposable container. It provides no evidence for production/staging privileges, traffic, availability, or deployment readiness.

## Recommended resolution

Keep this result as a local candidate pending Commander review. If accepted, authorize a separate, narrowly scoped runtime-wiring gate that binds the authenticated request principal to the lease arguments, invokes acquisition and validation as separate statements on the same transaction/connection, and tests the actual application dependency/session lifecycle. Do not deploy this candidate alone.

## Provenance and mutations

- Source baseline: `a2e3b3143b1d8e4c15c457e405fe7e349a973d3f`.
- Candidate migration parent: `20261006_0035`.
- Candidate migration: `20261007_0036` (uncommitted).
- Changed local files: candidate migration, qualification harness, this report.
- Database mutations: confined to the task-owned disposable PostgreSQL 16 container; no project/staging/production database was accessed.
- Docker mutations: task-owned ephemeral container only; stopped after final evidence capture; other containers untouched.
- Commit/push/CI/deploy: none.
- Final local worktree: candidate artifacts uncommitted; no unrelated tracked changes.
- Current corrected candidate SHA256: migration `0894DDAEA5AB8E1CCF67C93DFD8868A4E9AAA83F4B83641865CA918C0C397D7D`; harness `BA794218EA254B2E4F8CC819152FBEDF6F5EEDECF3CF8E16292033076EDD23A7`.


## A12TGIQR � owner provenance and lifecycle qualification

This section supersedes the A12TGIQ frozen candidate identity and its owner-reuse
qualification. The prior principal binding repair remains intact. No commit,
push, CI, staging, production, or deployment is authorized or performed.

### Dynamic finding before repair

Frozen migration SHA256:
`0894DDAEA5AB8E1CCF67C93DFD8868A4E9AAA83F4B83641865CA918C0C397D7D`.
On fresh task-owned PostgreSQL 16.15 (`codex-a12tgiqr-pg`, loopback port 3840,
database `a12tgiqr`), the database was explicitly advanced to 0035. A safe-attribute
`tenant_lease_owner` was pre-created, then granted to a disposable LOGIN role.
The frozen 0036 upgrade exited 0, retained that inbound membership, and the LOGIN
role successfully executed `SET ROLE tenant_lease_owner`. In a transaction,
`acquire_public_tenant_membership_lease(42,'a12tgiqr-probe')` returned true.
This demonstrates owner-helper reachability; it does not assert successful
membership validation or access to protected rows for that synthetic principal.
The frozen downgrade to 0035 succeeded and removed the owner role.

### Repair

- Reject any existing owner role before grants, helper creation, ownership or RLS
  changes. No existing role is reused, sanitized, altered, or revoked by upgrade.
- Create a fresh role with NOLOGIN, NOSUPERUSER, NOCREATEDB, NOCREATEROLE,
  NOINHERIT, NOREPLICATION and NOBYPASSRLS.
- Verify all seven inert flags and zero inbound/outbound pg_auth_members rows
  before helper ownership transfer. Repeat this invariant first on downgrade.
- Preserve the plain DROP ROLE lifecycle; no CASCADE or DROP OWNED.
- Remove the redundant owner-membership revoke from app_runtime. All function
  SQL bodies, locks, helper execution grants, PUBLIC revokes, and policy clauses
  remain unchanged relative to the frozen candidate.

### PostgreSQL qualification evidence

| Scenario | Result |
|---|---|
| Clean 0035 -> repaired 0036 | PASS |
| Pre-existing inert owner, zero members | Upgrade rejected; role and database snapshot unchanged |
| Pre-existing owner with LOGIN member | Upgrade rejected; membership and snapshot unchanged |
| Nested owner -> bridge -> LOGIN membership | Upgrade rejected; topology and snapshot unchanged |
| Pre-existing owner with outbound app_runtime membership | Upgrade rejected; topology unchanged |
| Downgrade with unexpected inbound LOGIN membership | Rejected, 0036 and policies/helpers preserved |
| Downgrade with unexpected outbound membership | Rejected, 0036 and all 12 policies preserved |
| Downgrade after unexpected INHERIT attribute | Rejected, 0036 and all 12 policies preserved |
| External table owned by owner | Plain DROP ROLE fails; transaction rolls back policy/helper changes; table preserved |
| Clean downgrade to 0035 and re-upgrade to 0036 | PASS |
| Final owner attributes / inbound / outbound memberships | All seven flags false / zero / zero |
| REPEATABLE READ and SERIALIZABLE | Acquisition false; protected SELECT zero rows |
| Full principal/tenant binding and forged-GUC regression | PASS |
| All 12 USING/WITH CHECK policies and valid RLS read/write | PASS |
| Lease-wins, revoke-wins, provision-wait concurrency | PASS |
| Mutation rollback and connection reuse | PASS |
| Ambiguous and suspended memberships | DENIED |
| app_runtime direct membership DML | NONE |

Failure snapshots compared revision, every tenant_isolation policy expression,
and lease-helper identity/owner. Rejected upgrades also compared owner pg_roles
metadata and the entire membership graph. Disposable fixture cleanup was explicit
and limited to this test database; the repaired migration never cleans up an
unexpected role or dependency.

Repaired artifact SHA256 (raw working-file bytes):
- migration: `78F1C630BF98253B9CADB971845BE690F355B8451F832B5DD9706A7B21A9DCBB`
- harness: `72EB841B22C57928537C708B3EA60E2454E6D0CAA16786460B306666915C8623`

Ruff, py_compile, compileall and git diff --check: PASS.
Canonical Linux x86_64 CPython 3.12 mypy baseline: PASS,
`MYPY_BASELINE=579 CURRENT=579 NEW=0 RESOLVED=0 UNCHANGED=579`.
The first read-only-container execution exited 2 without detailed gate output;
the same frozen dependency set then qualified in a task-owned Linux container
with `MYPY_CACHE_DIR=/tmp/mypy-cache`, without project or dependency-file repair.

SQL AST comparison against the frozen index confirmed that helper function
bodies, RLS policy clauses and function EXECUTE grants/PUBLIC revokes are exactly
unchanged. The unrelated checkout remains untouched; remote remains exact parent
`a2e3b3143b1d8e4c15c457e405fe7e349a973d3f`.

Task-owned PostgreSQL is stopped after qualification; the two task-owned quality
containers exited. All are retained for evidence, with no volume/image prune or
unrelated container action. Temporary dependency evidence lives outside Git.
Only the same three local candidate files changed; the index retains earlier
staged versions and the qualified repaired content is in the working files.
No commit, push, natural CI, external upload, staging or production change.

Final local verdict: `A12TGIQR_LOCAL_QUALIFICATION_PASS`.
Recommended next action: Commander review of the repaired frozen artifacts;
resume review under a separately issued Gate. A12TGIQ remains stopped.
