# Gate738B — Synthetic Migration & Lock Rehearsal Result

## Verdict

`PASS` — synthetic migration qualification criteria passed; `LOCK PROFILE: HIGH RISK`; production/staging migration and real restore remain blocked.

This qualification used synthetic data only in a new local disposable PostgreSQL 16/pgvector environment. No production or staging dump, rows, environment values, or credentials were used. One synthetic test-only credential was used only inside a disposable local database and was not written to this report. Production and staging remain outside this result.

## Environment and provenance

- Baseline revision: `20260921_0022`, reached by upgrading a fresh database from the repository's empty migration baseline.
- Candidate migration: `20260924_0023`; forward chain then reached `20261003_0026`.
- Image: cached `pgvector/pgvector:pg16`, local image ID `sha256:ccc6e83d6e35e931dc7c5def2022729d5a6c370318d099181995567ff1fb4d6b`.
- Isolation: Gate-owned container/network/volume with host binding `127.0.0.1:18567`; no Compose project, API, or other project was started or changed.
- Synthetic generator derived table relationships and constraints from the local canonical schema. Fixtures covered multiple students, reviewed/submitted/not-submitted states, legacy revisions, nullable content/timestamps, an old boundary timestamp, and existing reviews.
- The tested sizes were synthetic calibration tiers, not production estimates. Historical production row/size metadata was unavailable: `PRODUCTION SCALE CALIBRATION=UNKNOWN`.

## Scale results

Migration wall times include launching the Alembic process. Table storage is `pg_total_relation_size` for the three submission/review tables, which includes indexes; the index figure is a subset of that total.

| Tier | Submissions | Reviews | Status counts (submitted / reviewed / not submitted) | 0023 wall time | Table storage before → after 0023 | Index bytes before → after 0023 | 0024–0026 wall time |
|---|---:|---:|---|---:|---:|---:|---:|
| Small | 10 | 5 | 3 / 5 / 2 | 1,467 ms | 180,224 → 294,912 | 147,456 → 245,760 | 1,423 ms |
| Medium | 1,000 | 500 | 250 / 500 / 250 | 1,549 ms | 540,672 → 1,359,872 | 270,336 → 712,704 | 1,398 ms |
| Stress | 10,000 | 5,000 | 2,500 / 5,000 / 2,500 | 1,829 ms | 3,366,912 → 10,240,000 | 1,343,488 → 4,759,552 | 1,371 ms |

All three tier databases reached `20261003_0026`. Immediately after 0023, checks passed at every tier: original submission and review counts preserved; exactly one baseline revision per submission; current-revision pointers matched status; revision/submission tenant links and review links were valid; all generated revisions and review associations had the expected baseline provenance. No duplicate or lost rows were observed.

## Fail-closed invalid-state check

A separate 10-submission synthetic database included a review attached to a `NOT_SUBMITTED` row. Migration 0023 failed with the expected `Invalid legacy submission/review state; no repair authorized` error. `alembic_version` stayed at `20260921_0022`; `submission_revisions` was not created; all 10 submissions and 6 reviews remained present. This is an expected rejection and passed the fail-closed check.

## Post-migration security, application smoke, and repeatability

- `tests/test_gate736a_integrated_candidate_postgres.py` passed (`1 passed in 8.60s`) against the second isolated PostgreSQL 16/pgvector instance. It ran the integrated synthetic tenant membership, class enrollment, submission revision, review, and HTTP flows through 0026, including the test's runtime privilege checks and 0026 downgrade/re-upgrade exercise. All data and roles were confined to the disposable Gate738B cluster.
- Catalog checks on two identical, independently rebuilt 10-submission databases confirmed final revision `20261003_0026`, row counts `10 submissions / 5 reviews / 10 revisions / 5 linked reviews`, seven SECURITY DEFINER functions and seven `app_runtime` EXECUTE grants, `app_runtime` neither superuser nor BYPASSRLS, enrollment not executable by PUBLIC, and `submission_revisions` FORCE RLS plus its immutable trigger.
- Both databases began from the same empty-to-0022 baseline, received the same deterministic synthetic fixture, and independently migrated through 0026. Their normalized schema dumps had equal SHA-256 `9020123dea73aae28559c966f71cd4a71d82926af62cea89711266d1f304afd3`. Normalization removed only pg_dump's per-run random `\\restrict` / `\\unrestrict` wrapper tokens; schema and data integrity checks otherwise matched.
- Synthetic rebuild/re-migration repeatability: `PASS`.

## Draft migration runbook (planning only)

1. Before any separately authorized release, verify the exact environment, pinned candidate image digest, current database revision, PostgreSQL/Redis health, free storage, backup checksum and a valid restore-verification reference. Do not read or print secret values. Confirm the approved maintenance window and explicit abort thresholds.
2. Take and verify a fresh backup. If restore verification, current revision, image provenance, storage, or the maintenance window is missing, stop before migration.
3. Apply only explicit Alembic targets in order (`20260924_0023`, then `20261003_0024`, `20261003_0025`, and `20261003_0026`); never use `upgrade head`. Record start/end, resulting revision, lock waits, and affected row counts/metadata.
4. For 0023, monitor waits on both submission tables and API read/write behavior. Any wait or blocking beyond the approved threshold stops the release; preserve evidence and do not remove or weaken the migration lock. Verify transaction outcome and database revision before deciding the next action.
5. After 0026, verify revision, RLS/security functions and grants, app_runtime least privilege, PostgreSQL/Redis, health/readiness, and the approved critical application smoke suite.
6. If only the application fails while the database remains compatible, use the previously qualified, digest-pinned healthy image under its separate release approval. If database migration/recovery fails, stop writes and use restore-based recovery only from a verified backup under a separate authorized recovery procedure; do not downgrade across 0023.

This runbook is a synthetic rehearsal draft, not authorization for Production or Staging changes.

## Lock and concurrency result

A second disposable database used 1,000 synthetic submissions. A held read transaction acquired `ACCESS SHARE` locks on both legacy tables while migration 0023 requested `ACCESS EXCLUSIVE`.

- PostgreSQL observed the migration waiting on `student_submissions` with `wait_event_type=Lock`, `wait_event=relation`, mode `AccessExclusiveLock`.
- A new reader issued after the exclusive request was queued timed out at 1.2 seconds (`57014`).
- A writer timed out at 0.5 seconds (`55P03`); the attempted synthetic update did not commit.
- Releasing the read transaction allowed the migration to finish. Post-migration integrity checks passed.
- The measured 3,125 ms migration interval included the deliberately held lock (about 2,869 ms before release), so it is not a standalone migration runtime.

**Lock profile: HIGH RISK for availability during a queued exclusive lock.** Reads and writes can both be blocked. The local 10,000-row timing cannot predict production timing or outage duration. Do not weaken or remove the lock based on this rehearsal. Production rollout would require a separately approved maintenance/availability plan and production-scale metadata or rehearsal evidence.

## Cleanup and safety

Only the Gate738B-created databases, containers `ai-teacher-gate738b-postgres` and `ai-teacher-gate738b-requal-postgres`, their dedicated networks and volumes, and their synthetic roles were removed after verification. The pre-existing `ai-teacher-gate732-pg` remained running with restart count 0 on `127.0.0.1:8567`; it was not used or altered. Other Docker projects were not touched.

- Production/staging mutation: none
- Production dump or real data accessed/transferred: no
- Production/Staging API or Docker workload, environment, firewall, DNS, or Cloudflare changes: none; one isolated in-process HTTP smoke test ran against synthetic data
- Schema changes: only migration execution inside the disposable Gate738B databases, which were then removed
- Commit: none

## Recommended next decision

Keep real restore qualification blocked until an explicitly authorized isolated restore environment exists. Before planning any production application of 0023, decide whether its measured exclusive-lock availability risk is acceptable and provide production-scale table-size/row-count metadata through an approved, non-sensitive channel.
