# GateMAOS-A10 — Durable Persistence Foundation V1

## STATUS

`IMPLEMENTED_AND_QUALIFIED_ON_DISPOSABLE_POSTGRESQL_16`

`GateMAOS-A10` passed its focused persistence qualification. The full local suite is not green: one expected frozen-candidate-manifest closure failure and one environment failure caused by missing `mypy` package metadata remain. No commit, push, staging access, deployment, or production action occurred.

## Source and migration provenance

- Worktree: `D:\project\ai-teacher-maos-a5o`
- Branch: `codex/gate-maos-a5o`
- Qualified parent: `29edcfa3fc34c509eb0342ce84a8a16530e596a8`
- Live `origin/codex/gate731-target` at preflight: `29edcfa3fc34c509eb0342ce84a8a16530e596a8`
- Migration revision: `20261006_0034`
- Parent revision: `20261004_0033`
- Alembic heads after change: exactly `20261006_0034`
- Migration target used in PG16 test: explicit `20261006_0034`; no `head` target or stamp was used.
- Changes: the new A10 migration, its PG16 qualification test, and three test-only current-head expectation updates. No application/runtime code, workflow, dependency, earlier migration, MAOS authority source, or frozen manifest was modified.
- MAOS Kernel V1 source remains byte-identical to the qualified parent.

## Implemented persistence boundary

The migration creates the private `maos` schema and a `maos_audit_owner` role with `NOLOGIN`, `NOSUPERUSER`, `NOBYPASSRLS`, `NOCREATEDB`, `NOCREATEROLE`, and `NOREPLICATION`. The migration refuses unsafe existing owner attributes and refuses if `app_runtime` can inherit or assume the owner role. The migration role's temporary owner-role membership is revoked at the end of the migration.

The schema contains:

- `operation_reservations`, uniquely keyed by `(tenant_id, operation_id)`, with no expiry or purge mechanism. A replay with the same digest and operation kind returns the existing reservation; a mismatch fails closed. Digests are not globally unique.
- Tenant-scoped append-only `audit_events` and `effect_events`, using server-computed SHA-256 hash chains and monotonic per-stream sequence numbers. Mutable stream heads and effect-state projections are rebuildable projections, not independent trust anchors.
- Immutable `effect_intents`, one per tenant operation, with a deterministic provider idempotency key derived from tenant and operation identity. Critical risk is rejected. Effect states are `PREPARED`, `DISPATCHING`, `SUCCEEDED`, `FAILED`, and `UNKNOWN`; unknown outcomes can only move to a reconciled terminal state, never directly back to dispatching.
- Audit/effect metadata fields store digests and bounded reason/action codes only. No raw request, token, credential, secret, or provider response payload is persisted.

All six tables have both `ENABLE ROW LEVEL SECURITY` and `FORCE ROW LEVEL SECURITY`, with tenant policies that re-resolve the principal through the existing canonical membership resolver and reject a tenant selector that differs from that result. The runtime role has function execution only and no direct table `SELECT`, `INSERT`, `UPDATE`, `DELETE`, or `TRUNCATE` privileges. Existing writer-generation admission is attached to every new table. Authoritative record mutation and truncate triggers reject changes; foreign keys use `ON DELETE RESTRICT`, and downgrade is forward-only.

The application-authenticated principal ID remains an upstream trust input: PostgreSQL verifies its active canonical membership and does not trust the tenant selector, but this foundation does not independently authenticate an end user holding the shared runtime database credential. Runtime authentication adapters are outside this Gate.

No provider dispatch, provider call, approval/delegation record, account-lifecycle authority, runtime adapter, migration execution against shared staging, or production access was added.

## Qualification evidence

- Focused PG16 + migration-head/readiness/legacy-contract tests: `16 passed`.
- The opt-in integration test verified explicit target migration on a fresh disposable PG16 database, reservation replay/conflict/isolation/rollback, no global digest uniqueness, runtime table privilege denial, forced RLS tenant isolation and forged-selector denial, role attributes, audit SHA-256 recomputation, stable provider idempotency key, valid and invalid effect transitions, and absence of payload/secret-shaped columns.
- Test setup used a synthetic minimal prequalified `20261004_0033` predecessor fixture. It did not replay the entire historical migration chain; this is explicitly not claimed as a full-chain migration qualification.
- `ruff check`: PASS for all changed Python files.
- `py_compile`: PASS for all changed Python files.
- `git diff --check`: PASS.
- Disposable dump/restore smoke: NOT RUN. The A10 test qualification covered schema migration and database behavior; restore remains a separate required Gate before any external-effect use.
- Full local `python -m pytest -q`: `1232 passed, 24 skipped, 2 failed`.
  - `test_docker_copy_sources_are_candidate_manifest_covered` detects the new migration is absent from the frozen Gate738AD candidate manifest. That manifest and its extensions are intentionally frozen and were not edited; artifact provenance/build qualification requires a separate authorized Gate.
  - `test_mypy_execution_failure_fails_closed` cannot run in this host environment because the `mypy` distribution is not installed. No dependency was installed or changed.
- Mypy delta: NOT QUALIFIED in this host environment; the missing distribution is recorded above.
- Natural CI was not run: the authorized A10 scope prohibited commit/push, and it did not require a remote CI cycle.

## Risks and follow-up blockers

1. The frozen Gate738AD candidate manifest does not include `migrations/versions/20261006_0034_maos_durable_foundation.py`; candidate build-context provenance and artifact qualification are therefore blocked pending a separate manifest/source-extension Gate.
2. `app/api/routes/health.py` still expects runtime migration head `20261004_0033`. Runtime readiness/configuration was out of scope and unchanged; do not deploy this migration until a separate Gate aligns runtime readiness and qualifies the resulting artifact.
3. RPO/RTO, archival/retention policy, signing-key custody, and an external trust anchor remain later activation blockers. No automatic retention or deletion was implemented.
4. Providers without provider idempotency plus status/reconciliation support remain disabled. A10 provides persistence only.

## Final verdict

`MAOS_A10_PERSISTENCE_FOUNDATION_QUALIFIED_LOCALLY`

`CANDIDATE_ARTIFACT_NOT_QUALIFIED — SEPARATE PROVENANCE AND RUNTIME-READINESS GATE REQUIRED`

Mutations were confined to this isolated worktree and the disposable local PG16 qualification container/database. No shared staging or production resource was touched. No commit or push was created.
