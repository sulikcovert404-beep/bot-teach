# Gate738H — Compatibility Bridge Repair Qualification

> **Historical qualification record.** This report describes the former
> pre-control-plane lineage ending at `20261003_0031`; it is not evidence for
> the current release head. Gate738Y confirmed the current single head is
> `20261004_0033` and the staged path inserts `20261004_0032` before `0030`.
> The old Gate738F/H standalone runners are retired for current qualification.
> Their recorded historical results below remain evidence only for the
> disposable runs already completed at that time.

## Verdict

**`ROLLING_DEPLOYMENT_BLOCKED` — candidate implementation has promising disposable evidence, but Gate738H acceptance is incomplete.** This is not a release approval and authorizes no staging or production action.

## Scope and lineage

```text
Canonical worktree: D:\project\ai-teacher-gate731-target
Branch: codex/gate731-target
HEAD: e4140c4d55a2943c53ecc187a28729663073d48d
Candidate Alembic head: 20261003_0031 (single head)
Production/staging access or mutation: NONE
```

The candidate migration graph inspected here is `0027 -> 0028 -> 0029 -> 0030 -> 0024 -> 0025 -> 0026 -> 0031`, according to each file's `down_revision`; no `20260924_0023` file or reference is part of this candidate. The large set of earlier Gate and unrelated workspace changes predated this report and was not reset, cleaned, or committed.

| Revision file | SHA-256 in this worktree |
|---|---|
| `20261003_0027_submission_revision_parent_identity.py` | `DA114AD085304C17842FAAB41382A51968A6FB4B6AEEA524B2C405E4DB95E76B` |
| `20261003_0028_submission_revision_expand.py` | `D06D6D3B99E5ABDC97ED39DD681519E01C97933A1E26A210BC7125266E75720B` |
| `20261003_0029_submission_review_revision_index.py` | `C8D4A226649646DBB43A30BC59FB828564C2C111371A92C06AA16C690F8F957A` |
| `20261003_0030_submission_revision_contract.py` | `DA81FCFE614AC036123CB48539084F13576BA7E5CC0C1A6C1595D9179DC3C32F` |
| `20261003_0031_submission_revision_compat_cleanup.py` | `C1C82F9C8A602651E5760221593754F1C49F18C957B8AAB39CC45C6B64CFE6C6` |

These hashes identify local files only; they are not signed provenance or artifact attestations.

## Completed evidence

The repaired candidate migrations and `tests/gate738h_qualification.py` were run on two independent disposable PostgreSQL 16/pgvector clusters. Both clusters were subsequently removed. The synthetic harness reported:

- 200 row-lock race cases per cluster, split evenly between backfill-first and legacy-writer-first, preserving a revision-1 baseline and consistent current pointer.
- The actual resumable backfill worker processed the remaining synthetic rows.
- Candidate runtime service/review writes passed as `NOSUPERUSER`, `NOBYPASSRLS`; broad parent-column update, table delete, and review delete were denied. The exercised wrong-tenant read returned no rows and parent update affected zero rows.
- Short readers and representative writers during the 0030 migration had zero observed failures on the harness's 400-parent integration database.
- 0031 waited for the tested in-flight compatibility shared lock. After contraction, tested legacy parent update and legacy review insert failed with SQLSTATE `55000` without partial writes; the tested candidate revision write remained accepted.
- A 0030 failure probe in `PENDING` state left Alembic at 0029 with no partial contract constraints.
- Final tested counts reported zero missing current pointers and zero invalid review associations.

The separate scale rehearsal reported these synthetic values (including per-batch subprocess startup):

| Tier | Submissions / reviews | Backfill batches | Backfill elapsed | Missing pointers / unlinked reviews | 0030 / 0031 elapsed |
|---|---:|---:|---:|---:|---:|
| SMALL | 100 / 5 | 2 | 1.62 s | 0 / 0 | 1.71 s / 1.83 s |
| MEDIUM | 1,000 / 50 | 3 | 8.67 s | 0 / 0 | 1.88 s / 1.74 s |
| STRESS | 5,000 / 250 | 11 | 46.68 s | 0 / 0 | 2.48 s / 1.78 s |

Each scale tier reached `VALIDATED`. This was a sequential scale rehearsal; it did not run a concurrent reader/writer lock matrix at each scale tier.

Disposable requalification also completed:

```text
Gate733 tenant context PostgreSQL test: 1 passed
Gate735B class enrollment PostgreSQL test: 1 passed
Gate736A integrated candidate PostgreSQL test: 1 passed
Full pytest: 1000 passed, 11 skipped, 1 existing Starlette/httpx deprecation warning
compileall app tests: PASS
Ruff on candidate migrations/backfill/service and Gate738F/H + Gate733/735/736 harnesses: PASS
Alembic heads: 20261003_0031 (single head)
git diff --check: PASS (existing LF-to-CRLF warnings)
```

## Gate738H qualification continuation — 2026-10-04

After the disposable Docker daemon became reachable again, only the existing
Gate738H-owned PostgreSQL container was started. Inspection confirmed that it
uses only `codex-gate738h-freeze-data-20261003`,
`codex-gate738h-freeze-net-20261003`, and the loopback-only mapping
`127.0.0.1:18569 -> 5432`. No other container was started. The separately
protected `ai-teacher-gate732-pg` was observed in `Exited` state with restart
count zero; it was not touched.

The following additional checks passed on that isolated PostgreSQL 16 cluster:

| Probe | Observed result |
|---|---|
| ACL/RLS inventory | `INVENTORY_CAPTURED`; app_runtime is neither superuser nor RLS bypass; the three submission relations have RLS enabled and forced; exact column grants, 3 sequence grants, 6 SECURITY DEFINER functions, and 3 tenant policies were inventoried. Bridge functions are postgres-owned with fixed `search_path=pg_catalog`, and EXECUTE is revoked from PUBLIC and app_runtime. |
| Compatibility behavior | At 0029 and 0030, the app_runtime legacy parent/review SQL was accepted and bridged with revision integrity. Candidate service write passed at 0030. At 0031, legacy writes failed closed with SQLSTATE `55000` and no partial changes; candidate write passed. |
| Boundary failure injection | Baseline INSERT before/after, current-pointer UPDATE before/after, post-bridge review INSERT, mid-0030 DDL, and 0031 rollout UPDATE before/after all rolled back atomically. Alembic stayed at the preceding revision and rollout state stayed `COMPATIBILITY` after injected 0031 failures. Removing injections allowed 0031 to complete. |
| Backfill recovery | The real worker intentionally exited after one committed batch (`RUNNING`, 25/200 processed); a legacy update plus review during the pause preserved baseline/current snapshots. During resume, another legacy transaction held a row lock while the worker made later-batch progress; after commit, validation passed. Replay after `VALIDATED` left row counts and integrity unchanged (202 revisions, 1 review, zero invalid parents/reviews). |
| Main integration harness | 200 backfill/writer race pairs passed (100 each ordering); final head 0031; 605 revisions; zero missing current pointers and invalid review associations. The contract fence waited for an in-flight shared lock, legacy writes failed atomically, and candidate writes remained accepted. |

The lock matrix was rerun for all three data tiers while four reader loops and
two writers with a one-second lock timeout were active during 0030. The
observer watched `ACCESS EXCLUSIVE` specifically on `submission_reviews`;
it did not observe a wait event. These are synthetic loopback samples, not a
production traffic guarantee:

| Tier | Rows | 0030 elapsed | observed ACCESS EXCLUSIVE hold | reads / max / failures | writes / max / median / failures |
|---|---:|---:|---:|---:|---:|
| SMALL | 100 | 2137.13 ms | 74.11 ms | 1052 / 88.75 ms / 0 | 386 / 91.24 ms / 3.21 ms / 0 |
| MEDIUM | 1,000 | 1802.63 ms | 24.85 ms | 885 / 24.74 ms / 0 | 352 / 25.71 ms / 2.79 ms / 0 |
| STRESS | 5,000 | 1641.91 ms | 29.71 ms | 612 / 30.34 ms / 0 | 292 / 31.31 ms / 2.48 ms / 0 |

An initial rerun of the main harness with an unbounded writer loop stalled while
0030 waited for an `ACCESS EXCLUSIVE` relation lock. That harness process was
interrupted; its exact disposable test database was dropped. The harness was
then changed to use a finite 30-write burst, and the complete run above passed.
This was a harness-only adjustment; it is not evidence for unbounded writer
traffic. The dedicated per-tier matrix uses bounded lock timeouts.

Fresh full regression was run during this continuation; static checks were
rerun after the final harness-only edits:

```text
pytest: 1000 passed, 11 skipped, 1 Starlette/httpx deprecation warning
python -m compileall -q app tests: PASS
Ruff on Gate738H qualification runners: PASS
git diff --check: PASS (existing LF-to-CRLF warnings)
```

An additional dedicated loopback PostgreSQL fixture ran the existing lifecycle
and staged-migration suites after correcting its network from Docker `internal`
(which cannot publish a host port) to a dedicated bridge with a `127.0.0.1`
port binding:

```text
tests/test_submission_revision_lifecycle.py
tests/test_submission_revision_migration.py
16 passed
```

This adds live PostgreSQL evidence for wrong student-owner and tenant denial,
wrong teacher denial, limited-role RLS visibility and denied cross-tenant
revision insert, exact composite-FK/unique enforcement, immutable revision
rows, legacy bridge behavior, interrupted batch resume, and refusal to contract
invalid legacy review data. The first fixture attempt's 3 connection failures
were caused by its internal-only Docker network and were not product failures;
all 16 tests passed against the corrected isolated fixture.

The direct Gate738H ACL, lock, failure-injection, backfill-recovery, and main
qualification runners were also rerun successfully in this continuation.

### Docker-resumed ACL and PostgreSQL lifecycle recheck — 2026-10-04

After Docker became available, a new isolated PostgreSQL 16.15/pgvector
container was created under the exact names
`codex-gate738h-acl-20261004`,
`codex-gate738h-acl-data-20261004`, and
`codex-gate738h-acl-net-20261004`. Its only published endpoint was
`127.0.0.1:18571`. No other container was started or changed.

The Gate738H ACL inventory was expanded in the qualification runner (tests
only) and passed on a fresh migrated database:

```text
app_runtime: NOSUPERUSER, NOBYPASSRLS, NOCREATEROLE, NOCREATEDB, NOREPLICATION
public schema: USAGE only; CREATE denied
role memberships granted to app_runtime: none
default ACL entries: none
PUBLIC write/DDL grants across 48 public relations: none
submission RLS: enabled and forced on all three submission relations
targeted bridge functions: postgres-owned, fixed search_path, no PUBLIC/runtime EXECUTE
verdict: INVENTORY_CAPTURED
```

The PostgreSQL lifecycle and staged migration suites were rerun against that
same disposable cluster:

```text
tests/test_submission_revision_lifecycle.py
tests/test_submission_revision_migration.py
16 passed in 20.76s
```

After the ACL-runner expansion, the full repository suite was rerun in the
current worktree:

```text
pytest: 1000 passed, 11 skipped, 1 existing Starlette/httpx deprecation warning
```

The exact Gate-owned container, volume, and network were removed after the
tests; inspection confirmed they are absent. The protected
`ai-teacher-gate732-pg` remained `Exited` with restart count zero. No other
project container, volume, or network was modified. The only workspace change
in this recheck was the ACL qualification harness and this report.

## Acceptance gaps / blockers

Gate738H cannot be marked complete because the following required qualification evidence was not produced:

1. **Privilege and adversarial matrix remains partial.** The updated inventory covers targeted roles, schema, relation/column/sequence grants, bridge and tenant SECURITY DEFINER function ownership/settings/EXECUTE rights, and RLS policies. PostgreSQL lifecycle tests now prove wrong student-owner/tenant and wrong-teacher denial, plus an RLS-limited principal's cross-tenant isolation. The full authenticated HTTP role matrix, foreign-assignment case, legacy-admin behavior, direct function abuse, and broader PUBLIC/default-ACL paths were not all exercised.
2. **Actual rolling-version overlap and old-writer drain remain unproven.** The compatibility matrix exercises candidate service behavior and representative legacy SQL as `app_runtime` at 0029, 0030, and 0031. It does not run a captured prior application artifact or enumerate/drain all live old-runtime instances. A database singleton fence cannot prove that every old application process has stopped issuing requests. 0031 rejects legacy writes; an old process still running at cutover can therefore fail.
3. **Lock evidence is still bounded and partial.** The SMALL/MEDIUM/STRESS concurrent matrix completed with zero observed reader/writer failures and no observed wait on `submission_reviews` ACCESS EXCLUSIVE. It does not observe every relation/lock mode, does not model production load, and does not prove behavior under indefinite writer saturation. The unbounded harness stall is recorded above.
4. **Detailed scale metrics remain incomplete.** Prior sequential scale measurements cover backfill/0030/0031 elapsed times and data sizes, and the new matrix adds per-tier lock samples. Expansion duration and batch timing distributions for every tier, broader index-size deltas, and production-calibrated traffic are still absent.

Accordingly, no claim is made that all Gate738H acceptance criteria, all Gate732–736 requalification, or a safe rolling deployment have passed. The broad pytest result does not replace these focused operational and security qualification gates.

## Safety record

```text
Production access/mutation: NONE
Staging access/mutation: NONE
Database writes: isolated synthetic disposable databases only
DB migration outside disposable test clusters: NONE
Image build/pull/push or deployment: NONE
Protected ai-teacher-gate732-pg: observed Exited, restart count 0; not touched
Other Docker projects: not started or modified by this continuation
Commit: NONE
```

After the qualification runs, both Gate738H-only disposable PostgreSQL
containers, their dedicated volumes, and their single-purpose networks were
removed. This also removed six Gate738H synthetic databases found in the first
cluster. Verification confirmed the exact resource names are absent and
`ai-teacher-gate732-pg` remains `Exited` with restart count zero. No Docker
prune, protected-container restart, or broad cleanup was run.

## Recommended next work

Keep the candidate blocked. The synthetic qualification gaps above can be
addressed in another disposable-only Gate. Before any shared 0031 operation,
require an independently verifiable old-runtime artifact and an operational
drain proof, plus a bounded lock/cutover plan. No such shared-environment
operation is authorized by this report.
