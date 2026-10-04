# Gate738F — Online Migration Rollout Qualification

## Verdict

**`GATE738F_BLOCKED`**

The disposable scale, resume, fail-closed recovery, independent-cluster, and regression checks passed. Gate738F cannot qualify rollout because overlapping legacy writes can omit a pre-existing baseline snapshot, the migration-only `app_runtime` role cannot execute the candidate service's direct table operations, the old writer is incompatible after revision 0031, and the 0030 contract requests an `AccessExclusiveLock` that blocks a writer behind a held reader.

These are qualification findings, not authorization to repair or deploy. Candidate migration files were not edited. Production and staging were not accessed or changed. Real backup restore remains unverified (`Gate738A=REHEARSAL_ENV_BLOCKED`).

## Frozen candidate and environment

```text
Canonical worktree: D:\project\ai-teacher-gate731-target
Branch: codex/gate731-target
HEAD: e4140c4d55a2943c53ecc187a28729663073d48d
Alembic head: 20261003_0031
```

All five migration SHA-256 values still match the Gate738G-recovered candidate bytes:

| Revision | SHA-256 |
|---|---|
| `20261003_0027_submission_revision_parent_identity.py` | `DA114AD085304C17842FAAB41382A51968A6FB4B6AEEA524B2C405E4DB95E76B` |
| `20261003_0028_submission_revision_expand.py` | `411345DBA09A3D9F7E7F9B1C5364D9E03CFDC85876F9468D447C6554D3D808DB` |
| `20261003_0029_submission_review_revision_index.py` | `C8D4A226649646DBB43A30BC59FB828564C2C111371A92C06AA16C690F8F957A` |
| `20261003_0030_submission_revision_contract.py` | `0EC1A23855137F1608D0C04918E2AAC18521E70DC3F35972E88A5768A8C4BCBA` |
| `20261003_0031_submission_revision_compat_cleanup.py` | `821C60545969A177EA175AA4A5EDBFA75655D0FE1AB7BE67B6299FE279BA3232` |

Two Gate-owned PostgreSQL 16/pgvector containers used separate networks, volumes, and loopback ports. Cluster one ran on `127.0.0.1:10702`; cluster two on `127.0.0.1:5201`. Both were removed with their exact dedicated volumes and networks after qualification. The pre-existing `ai-teacher-gate732-pg` remained running on `127.0.0.1:8567`, restart count `0`. No other Docker resource was touched.

## Phase results

### Phase 2 — Scale matrix: PASS, synthetic only

Each tier began at 0022, applied 0027–0029, backfilled in bounded resumable batches, validated, and completed 0030–0031. Process launch time is included in the reported timings. These figures are not production estimates.

| Tier | Submissions / reviews | Backfill subprocess batches | Backfill elapsed | Median / max batch subprocess | Revision rows | Missing pointers / unlinked reviews | Submission + review + revision storage after |
|---|---:|---:|---:|---:|---:|---:|---:|
| SMALL | 100 / 5 | 2 | 1.96 s | 0.98 / 1.35 s | 100 | 0 / 0 | 155,648 + 98,304 + 131,072 B |
| MEDIUM | 1,000 / 50 | 3 | 9.86 s | 4.08 / 5.27 s | 1,000 | 0 / 0 | 614,400 + 131,072 + 368,640 B |
| STRESS | 5,000 / 250 | 11 | 47.37 s | 4.58 / 5.20 s | 5,000 | 0 / 0 | 2,416,640 + 245,760 + 1,376,256 B |

Table storage before the backfill was 147,456 + 98,304 B (SMALL), 352,256 + 98,304 B (MEDIUM), and 1,261,568 + 147,456 B (STRESS) for submissions and reviews, respectively. Backfill state reached `VALIDATED` at every tier with the expected processed counts.

### Phase 3 — Interruption and resume: PASS

Every scale tier paused after a committed bounded batch and resumed to validation. The focused migration tests also confirmed the persisted checkpoint and final contract. Final row, pointer, and review checks passed on the scale databases.

### Phase 4 — Concurrent legacy writers: FAIL — baseline state loss

On a 5,000-submission synthetic database, the backfill worker was confirmed still running at the write point (`processed_submissions=100`, worker alive). A legacy update advanced an unprocessed parent from revision 1 to revision 2 while adding a review; writes also created a new submission and reviews for a migrated parent and a not-yet-backfilled parent. After the worker resumed and completed, current pointers and review links were valid, but the updated unprocessed parent had **zero revision-1 snapshots** and only its revision-2 compatibility snapshot. The old baseline content was therefore absent from the revision history.

The end-state checks alone would have looked clean (`missing pointers=0`, `unlinked reviews=0`, `5,001 submissions / 5,001 revisions`). The revision-history invariant did not pass. The candidate needs a separately approved design/repair and a repeat of the overlap test before this phase can pass.

### Phase 5 — Least-privilege runtime role: BLOCKED

An isolated cluster created `app_runtime` before applying the candidate chain. It was `NOSUPERUSER`, `NOBYPASSRLS`, without `CREATEDB` or `CREATEROLE`. The candidate granted the role `SELECT`/`INSERT` on `submission_revisions` and sequence `USAGE`, while `UPDATE`/`DELETE` on revisions remained denied. However, this migration-only role had no `SELECT` or `UPDATE` on `student_submissions`, and no `SELECT`/`INSERT` on `submission_reviews`; a direct parent-table `SELECT` failed with SQLSTATE `42501`.

The candidate application service directly selects and updates the parent row and reads/writes reviews. Its actual runtime grants may be provisioned outside these migrations, but those exact grants were not available in this disposable model. Thus application-role compatibility is **not qualified**. No grants were added to the candidate or any real environment. Catalog review found the seven SECURITY DEFINER operations owned by the migration identity, with `search_path=pg_catalog`, runtime EXECUTE, and no PUBLIC EXECUTE; this does not resolve the missing table privileges for the direct ORM path.

### Phase 6 — Runtime compatibility: `ROLLING_DEPLOYMENT_BLOCKED`

Existing tests passed legacy writes while the 0028 bridge was present. A synthetic legacy writer was then exercised after 0031, when the bridge triggers had been removed. Its permitted legacy update changed the parent to revision 2 while the current pointer still referenced revision 1; parent revision/content no longer matched the pointed-to snapshot. A legacy review insert without the new required association columns failed with SQLSTATE `23502`. The probe transaction was rolled back.

The old runtime must be drained before 0031, and any mixed-version window through the final contract still requires exact runtime grants and requalification. Gate738F does not authorize a rollout.

### Phase 7 — Lock matrix: `LOCK_RISK_REMAINS`

With 5,000 synthetic submissions backfilled, a held reader caused revision 0030 to wait on a relation lock while adding `ck_submission_current_revision` to `student_submissions`. PostgreSQL reported `wait_event_type=Lock`, `wait_event=relation`, and an ungranted `AccessExclusiveLock`. A writer issued while that request was queued timed out at the 1-second probe limit. Releasing the reader let 0030 complete. The observed total contract elapsed time was 2.84 seconds including the deliberately held reader; it is not a standalone migration duration.

This demonstrates a reader/writer availability block under a queued exclusive request. No production-scale lock duration is inferred.

### Phase 8 — Failure and recovery: PASS for tested synthetic case

A review attached to a `NOT_SUBMITTED` row caused backfill validation to stop at revision 0029 with state `RUNNING` and `DO NOT CONTRACT`. Applying 0030 before validation was refused. After removing only that deliberately invalid synthetic review, the worker resumed successfully; a second run while `VALIDATED` also succeeded. The chain reached 0031 with two valid revisions, zero missing pointers, and zero unlinked reviews. This qualifies the tested correction-and-resume path; it is not a general rollback or restore qualification.

### Phase 9 — Independent cluster repeatability: PASS

The full 0022→0027–0031 chain was run with synthetic data in two separate disposable PostgreSQL clusters. Cluster one completed the three scale tiers through 5,000 submissions; cluster two independently completed a 1,000-submission tier and the isolated runtime-role setup. Both reached 0031 and passed the applicable integrity checks.

### Phase 10 — Regression and static checks: PASS

```text
Focused Gate732–736 / revision / tenant checks: 19 passed, 3 skipped
Full pytest suite:                            1,003 passed, 8 skipped
Ruff (candidate migrations, backfill, service, focused and Gate738F harnesses): PASS
compileall app and tests:                     PASS
git diff --check:                             PASS (line-ending warnings only)
```

The full suite emitted one existing Starlette/httpx deprecation warning. The skipped tests were reported as skipped by pytest; they are not counted as passes.

## Files, mutations, and limits

Only Gate738F qualification harnesses were newly added under `tests/`:

- `tests/gate738f_qualification.py`
- `tests/gate738f_concurrency.py`
- `tests/gate738f_lock.py`
- `tests/gate738f_recovery.py`

The candidate migration files 0027–0031 were not edited; their recorded SHA-256 values were rechecked after testing. No production/staging access, migration, restore, deploy, image operation, commit, or application-semantic change occurred. Synthetic database and test-role mutations remained inside the two Gate-owned disposable clusters and were removed with those clusters.

The worktree already contained other Gate732–738 candidate files and unrelated modifications before this report; they were not reset, cleaned, or committed. No production restore was attempted. A Gate738F pass must not be interpreted as production migration approval.

## Required next decision

Keep migration execution on `HOLD`. Issue a separate repair/design Gate addressing (1) preservation of the pre-existing baseline under concurrent legacy updates, (2) the exact least-privilege `app_runtime` boundary for the direct service path, (3) old-runtime drain and final cleanup compatibility, and (4) the measured 0030 exclusive-lock availability risk. Then repeat the affected phases on two fresh disposable clusters before any later release decision.
