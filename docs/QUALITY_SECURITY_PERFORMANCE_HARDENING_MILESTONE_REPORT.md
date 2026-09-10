# Quality, Security, Performance Hardening Milestone Report

## Status
PARTIAL — council review completed; implementation and runtime validation remain pending Commander decisions and clean evidence.

## Completed
- Sanitized security handoff created and pushed at `temp/agent-handoffs/2026-09-10-security-hardening/`.
- Claude Sonnet 5 review completed and recorded.
- Council consolidation recorded in `docs/SECURITY_ARCHITECTURE_COUNCIL_REVIEW.md`.
- Production unchanged; no RLS/schema/migration mutation performed.

## Critical findings open
- Retrieval `scope` enforcement requires direct code/test validation.
- Tenant isolation has no demonstrated database-level backstop in supplied evidence.
- Sanitized auth excerpt is structurally corrupted; JWT secret validation cannot be confirmed.
- Credential rotation and destructive re-ingestion remain previously reported blockers pending current-state verification.

## High findings open
- Teacher tenant/class authorization implementation not included in handoff.
- Retrieval publication-pointer usage and audit-log immutability require verification.
- Critical-path regression, failure, load, and restore evidence not yet collected in this turn.

## Agent verdicts
- Claude: confirmed several evidence-backed retrieval/tenant gaps; RLS_SELECTED_TABLES recommendation, no migration authorization.
- GLM: prior advisory review identified cross-tenant, entitlement, RAG, session, audit, and RLS risks.
- Qwen: no new security handoff response in this round; prior response is unrelated and excluded from consensus.

## RLS recommendation
RLS_SELECTED_TABLES is a council recommendation only. No RLS migration may be prepared or applied until Commander selects and approves exact tables, policies, bypass rules, pool strategy, rehearsal, and rollback.

## Validation state
Tenant/Auth isolation: PARTIAL
RAG leakage: PARTIAL (scope gap requires focused tests)
Performance/load: NOT RUN
Failure handling: NOT RUN
Backup/restore: NOT RUN
Observability: PARTIAL
Full regression: NOT RUN

## Next recommended task
Codex should isolate and validate the retrieval scope path and auth/tenant authorization evidence with focused tests, then request Commander decision before any schema or RLS work. Existing broad working-tree modifications must be preserved and reviewed before changes.

## Production
UNCHANGED

## Additional focused validation (2026-09-10)
- 	ests/test_admin_authorization.py, 	ests/test_authorization_wiring.py, 	ests/test_assignment_contract.py: 11 passed.
- This validates pure role/ownership contracts only; it does not prove database-level tenant isolation or RLS.


- Persistence/content/admin/Telegram route suite: 19 passed (one dependency deprecation warning). This confirms route behavior under test fixtures, not cross-tenant isolation against real PostgreSQL.

- Targeted focused suite rerun: 11 passed in 0.15s.
- Ruff could not be executed in the current Windows environment (`python -m ruff`: module unavailable); no lint pass is claimed.

## Retrieval scope audit (2026-09-10)
- `ScopedDatabaseRetriever` does apply tenant, classroom, grade, publication, approval, processing, and vector-sync predicates before lexical ranking.
- `PgVectorStore.search` still accepts no tenant/classroom/scope fields and filters only source metadata; it cannot independently prove tenant isolation or publication eligibility.
- `SourceChunk` has no persisted `scope` column, while the provider-neutral RAG contract exposes `scope`; this remains an adapter/schema integration gap.
- No code fix was applied pending Commander selection of the RLS and canonical retrieval boundary.
- Existing `tests/test_vector_store.py` covers PostgreSQL gating, invalid-input rejection, and pgvector DDL compilation only; it contains no query-level tenant/publication/scope isolation assertion.
- Combined security/retrieval contract suite: 24 passed in 1.33s (`vector_store`, `knowledge_runtime`, `rag_contracts`, `publication_access`, assignment, admin authorization, and authorization wiring). These remain unit/contract checks and do not replace a real PostgreSQL isolation test.

## Staging runtime recheck (2026-09-10)
- Before the Docker daemon became unavailable, `stagingwave-api-pub` was observed `unhealthy`; repeated `/health/ready` probes returned HTTP 503 with `Migration drift / Not ready`.
- A follow-up `docker exec`/`docker version` could not reconnect because the Docker Desktop Linux engine named pipe was absent. Revision and expected-head comparison therefore remains unverified in this recheck.

- Docker was subsequently available; staging services were started with the existing compose definition. `stagingwave-db-1` and `stagingwave-redis-1` are healthy, migration exited 0, and `GET http://localhost:8000/health/ready` returned HTTP 200 with migration head `20260909_0015`.
- The orphan `stagingwave-api-pub` container remains stopped; it was not removed or modified.

- Official `scripts/staging-smoke.ps1` was attempted with PowerShell execution-policy bypass. Database/Redis/migrate reached healthy/exit-0, but API startup failed because port `0.0.0.0:8000` is already allocated by healthy `stagingwave-api-1` from the other compose project. No container was stopped to force the test.
- Direct readiness probe against the already-running staging API passed: `{"status":"ready","migration_head":"20260909_0015"}`. The script default still expects `20260907_0008`, so its expectation is stale relative to the running staging lineage.
- Read-only endpoint smoke: `/health` returned HTTP 200 and `/openapi.json` returned HTTP 200. The expected liveness route is `/health` (not `/health/live`); `/health/live` returned 404.
- Health/database contract tests: 6 passed in 15.31s; two existing deprecation warnings were emitted (Starlette/httpx and Alembic `path_separator`).
- Follow-up runtime check: all three `stagingwave` services healthy; container environment and readiness both report `EXPECTED_MIGRATION_HEAD=20260909_0015`.
- Container lint audit (`ruff check --no-cache`) completed after rebuild but reports 78 findings across the selected files (notably import ordering/unused imports, FastAPI `Depends` defaults, timezone calls, executable-bit/shebang checks, and one nested-if simplification). No auto-fix was applied; these findings require scoped review to avoid unrelated behavior changes.
- Local Alembic source audit reports two heads (`20260909_0009` and `20260909_0015`) and a branchpoint at `f7a8b9c0d1e2`; this is a migration-lineage risk requiring Commander review. `alembic current` could not run locally because the local database URL is not configured. No merge migration or schema change was created.
- Head ancestry confirms `20260909_0009` descends from `2e0b56730806`, while `20260909_0015` descends through `20260909_0014`; the parallel heads are genuine lineage divergence, not a display artifact.
- Container image audit adds drift: `docker exec stagingwave-api-1 alembic heads` reports `20260909_0009` and `20260909_0014`, while the database/readiness reports current `20260909_0015`. Readiness currently checks the database value against environment, not that the deployed image's migration source contains that revision. This is a release validation gap; no migration or image change was made.
- File-level check confirms workspace contains `migrations/versions/20260909_0015_assignment_persistence.py`, while the running image has no matching `*0015*` migration file.
- Official smoke script passed when run against the active `stagingwave` compose project with explicit `-ExpectedMigrationHead 20260909_0015` and `-BaseUrl http://localhost:8000`. Database/Redis health, migration completion, and readiness all passed; the orphan container warning remains informational.

