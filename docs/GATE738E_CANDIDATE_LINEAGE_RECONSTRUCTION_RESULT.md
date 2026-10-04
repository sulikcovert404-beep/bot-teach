# Gate738E — Candidate Lineage Reconstruction & Online Migration Qualification

**Scope:** current workspace and one isolated, loopback-only disposable PostgreSQL cluster.  
**Production/Staging:** not accessed or changed. **Commit/deploy:** none.  
**Final:** `CANDIDATE_QUALIFICATION_PASS_WITH_LIMITS`; Production migration remains `NO-GO`.

## Finding and lineage

The lost candidate revision `20260924_0023` remains `LOST_UNRELEASED`. Its previously recorded SHA-256 is `79132ca63ed00786921be8a04c6313d9f508c9ddb57b5e4f02fb3faed538eeaf`; the source bytes are unavailable in this workspace and the recorded image-source commit is not available in the local Git object database. The revision was not recreated or reused.

Commander authorized a new, uniquely identified replacement candidate and full requalification, strictly on disposable local PostgreSQL. The replacement chain is:

```text
20260921_0022
  -> 20261003_0027 parent identity index
  -> 20261003_0028 additive schema and legacy compatibility bridge
  -> 20261003_0029 concurrent review index
  -> 20261003_0030 validated contract
  -> 20261003_0024 tenant context
  -> 20261003_0025 membership operations
  -> 20261003_0026 enrollment operations
  -> 20261003_0031 compatibility cleanup
```

The workspace Alembic head resolves to `20261003_0031`. The current local `20260921_0022_provisioning_idempotency.py` SHA-256 is `cfe5045c895894469f953ce2c3bdb9fc61713dd8d99261fd5c5a216a40bd47c6`, matching the hash retained in earlier Gate evidence; its claimed source commit could not be independently read from this machine's object database. Revisions 0024–0026 remain local, unreleased candidates and now depend on 0030. No evidence collected in this Gate changes the earlier read-only Production observation of revision 0022.

## Implementation and qualification evidence

The replacement candidate implements concurrent identity-index preparation, an additive revision schema with compatibility triggers, a restartable bounded backfill worker, a validation-gated contract, and a final compatibility-trigger cleanup revision. The worker refuses non-loopback connections and database names outside `gate738e_*`, requires an explicit disposable-run flag, and emits aggregate counts rather than a DSN or row payloads.

SHA-256 of the exact local candidate files qualified here:

| File | SHA-256 |
|---|---|
| `migrations/versions/20261003_0027_submission_revision_parent_identity.py` | `DA114AD085304C17842FAAB41382A51968A6FB4B6AEEA524B2C405E4DB95E76B` |
| `migrations/versions/20261003_0028_submission_revision_expand.py` | `411345DBA09A3D9F7E7F9B1C5364D9E03CFDC85876F9468D447C6554D3D808DB` |
| `migrations/versions/20261003_0029_submission_review_revision_index.py` | `C8D4A226649646DBB43A30BC59FB828564C2C111371A92C06AA16C690F8F957A` |
| `migrations/versions/20261003_0030_submission_revision_contract.py` | `0EC1A23855137F1608D0C04918E2AAC18521E70DC3F35972E88A5768A8C4BCBA` |
| `migrations/versions/20261003_0031_submission_revision_compat_cleanup.py` | `821C60545969A177EA175AA4A5EDBFA75655D0FE1AB7BE67B6299FE279BA3232` |
| `scripts/backfill_submission_revisions.py` | `4EC847DE7E0A231C3174F08053BA21CAF79CE7EC775BE61951187A3AD7308B8E` |

On the new disposable PostgreSQL 16 cluster, staged tests exercised:

- upgrade from 0022 through expand and concurrent-index revisions;
- synthetic baseline rows, current-pointer and review association backfill;
- interruption after one committed batch and successful resume from persisted progress;
- legacy-format submission and review writes while the compatibility bridge exists;
- invalid review-on-unsubmitted data, which remained at expanded revision 0029 with backfill state `RUNNING`; contract upgrade refused to proceed;
- successful contract through 0031, including composite ownership/foreign-key and uniqueness enforcement and immutable revision rows;
- candidate application lifecycle, idempotent replay/conflict handling, review/feedback behavior, and tenant RLS checks on a disposable non-superuser probe role.

Results:

```text
Focused migration/lifecycle/health/graph tests: 23 passed
Full workspace regression:                    1000 passed, 11 skipped
Compile checks:                                PASS
Alembic head:                                  20261003_0031
Ruff on new migrations/backfill/lifecycle tests: PASS
```

The only warning in the full suite was an existing Starlette/httpx deprecation warning. The synthetic invalid-data test demonstrated fail-closed behavior; it did not repair the invalid row.

## Compatibility, rollout and recovery boundary

The compatibility trigger was exercised with a synthetic legacy writer under the disposable database's administrative identity. The candidate lifecycle and RLS behavior were exercised separately under a restricted disposable role. A simultaneous run of the actual 0022 application identity against the expanded schema, concurrent application writes during backfill, rolling multi-instance deployment, and failure recovery against a restored production-sized backup were **not** qualified.

The health endpoint allows an expected-head override through `expected_migration_head`; the code default is 0031. A future deployment plan must explicitly qualify the transitional candidate at head 0026 while the bridge remains, then switch readiness expectation to 0031 after old writers are drained and 0031 removes the bridge. Do not deploy the current default-head build against an earlier head and assume readiness. The bridge must remain until every old runtime instance is confirmed drained. Once 0031 is applied, rollback to a legacy 0022 application is not qualified and must not be assumed safe.

Recommended order for a separately authorized execution plan:

1. Qualify a fresh backup by an actual isolated restore and capture the approved rollback/recovery procedure.
2. Apply 0027–0029 while the 0022-compatible runtime is available; retain the bridge.
3. Run the resumable backfill in bounded batches, monitor lag and lock/latency indicators, and require all validations to pass before continuing.
4. Apply 0030 only inside a measured, approved cutover window. It validates constraints and sets required columns `NOT NULL`; this Gate did not establish a Production lock-duration bound.
5. Apply 0024–0026, then deploy a candidate that is qualified for head 0026 with the bridge still present. Drain and verify all legacy writers.
6. Apply 0031 only after the compatibility boundary is closed; then require head 0031 readiness. Keep rollback on the candidate-compatible side of this boundary.

This order is a planning recommendation, not deployment authorization. In particular, the transitional head override and mixed-version deployment order need a dedicated rehearsal before any live execution.

## Risk and remaining qualification

- **Production scale and workload:** unknown. The rehearsal used a few synthetic records and did not run SMALL/MEDIUM/STRESS volume calibration. No production table rows or payloads were read in this Gate.
- **Lock windows:** concurrent index operations ran successfully on the disposable database, but individual lock duration and impact under concurrent readers/writers were not measured. Constraint validation scans and `SET NOT NULL` in 0030 require separate lock and duration qualification against representative scale.
- **Legacy least-privilege bridge:** not tested with the actual `app_runtime` identity and its exact production grants/policies. A superuser synthetic legacy write is not proof of runtime-role compatibility.
- **Backup/restore and recovery:** no restore, rollback-image qualification, Production/Staging action, or recovery-time rehearsal occurred. Historical archive listing/checksum evidence is not a restore test.
- **Artifact provenance:** candidate files are workspace-only and uncommitted. The unavailable 0023 source and unavailable Git source object for 0022 limit independent provenance verification; this Gate qualifies behavior of the replacement bytes tested here, not a released artifact.

These gaps keep live migration blocked pending representative load/lock qualification, real-role compatibility, a successful restore rehearsal, and a separately approved execution plan.

## Resource and mutation accounting

Created only for this Gate: `codex-gate738e-net-20261003`, `codex-gate738e-pg-20261003`, `codex-gate738e-db-20261003`, loopback port `127.0.0.1:18568`, and databases named `gate738e_*`. All were removed after testing. The pre-existing `ai-teacher-gate732-pg` remained `Up` on `127.0.0.1:8567`; no other Docker resource was stopped, restarted, renamed, or removed. No production/staging database, secret, environment file, DNS, firewall, or service was touched.

**Migrations executed:** disposable local databases only. **Production/Staging migration:** none. **Commit:** none.

## Verdict

`CANDIDATE_QUALIFICATION_PASS_WITH_LIMITS` — the replacement migration flow and candidate behavior passed the stated small disposable rehearsal and regression suite. This is not a Production readiness verdict. Production migration remains `NO-GO` until the remaining scale, lock, least-privilege compatibility, restore, and rollout qualifications are closed by separately authorized Gates.
