# Gate 736A — Integrated Local Release Candidate Qualification

Date: 2026-10-03

## Verdict

`BLOCKED — GATE736A_FULL_REGRESSION_HARNESS_BLOCKED`

The integrated candidate path passed against one fresh disposable PostgreSQL database, including migration round-trip and the combined membership, enrollment, assignment, submission, review, and revocation flows. Full repository regression did not finish green: the checkout lacks two modules imported by tests, and the runnable suite has 19 HTTP 429 failures that disappear when the affected test modules run in isolated processes. Do not treat the complete release candidate as fully qualified until the full-suite harness has a clean run.

## Candidate and migration lineage

- Branch: `codex/gate731-target`
- HEAD: `e4140c4d55a2943c53ecc187a28729663073d48d`
- Alembic heads: exactly `20261003_0026`
- Migration chain through `20261003_0026` exists in the workspace; the integrated test upgraded a fresh database to that explicit revision, downgraded to `20261003_0025`, and upgraded again successfully.
- `python -m compileall -q app migrations tests`: PASS
- `git diff --check`: PASS (Git emitted line-ending normalization warnings only)
- Ruff over the 27 changed/new Python files: 72 current findings versus 81 in the corresponding HEAD baseline; multiset comparison by rule and message found 1 net-new `B008` finding in `app/api/routes/student.py`. The candidate is therefore not Ruff-clean, and this new finding remains recorded rather than silently fixed during qualification.

## Integrated disposable PostgreSQL qualification

Test: `tests/test_gate736a_integrated_candidate_postgres.py`

Result: `1 passed` (8.81 seconds).

One fresh PostgreSQL 16/pgvector database was used for the integrated flow. It verified the 0026 schema and required function/role boundaries; tenant-membership create and replay; SUPER_ADMIN tenant bootstrap and replay; same-target concurrent provisioning; competing-tenant provisioning with one success and one conflict; authorization denials for anonymous, wrong-role, and cross-tenant enrollment attempts; enrollment and duplicate-enrollment concurrency; assignment access only after enrollment; idempotent submission/replay and conflicting payload rejection; revision sequence and teacher review/history; class-membership removal revoking assignment access while retaining tenant membership; tenant-membership revocation denying subsequent protected access; the retired legacy teacher write endpoint returning 410; and downgrade/re-upgrade round-trip.

Disposable resources were Gate-owned and loopback-only:

- Container: `codex-gate736a-postgres`
- Image: `pgvector/pgvector:pg16`, local image ID `ccc6e83d6e35`; immutable image ID digest `sha256:ccc6e83d6e35e931dc7c5def2022729d5a6c370318d099181995567ff1fb4d6b`
- Network: `codex-gate736a-net`
- Volume: `codex-gate736a-data`
- Port: `127.0.0.1:8572 -> 5432`

The existing `ai-teacher-gate732-pg` on `127.0.0.1:8567` remained running and was not used or modified.

## Regression and collection

- Full `python -m pytest -q` collection is blocked by absent workspace modules imported by tests: `scripts.postgresql_backup` and `scripts.r2_offsite_packager`. These files were not created because that is outside qualification scope.
- Runnable regression excluding those two test modules: `971 passed, 11 skipped, 19 failed`.
- The 19 failures are HTTP 429 rate-limit responses from cumulative in-memory limiter state in the shared pytest process. Each affected test module passed when run in a fresh isolated process; the corrected per-file reruns totaled 47 passed and 4 skipped across the affected modules.
- This isolated-process evidence supports a test-harness interaction finding, but it does not convert the full regression run into a pass.

## Route compatibility evidence

Repository search found the mini-app calling `GET /api/v1/student/v1/assignments`. No in-repository active callers were found for the changed tenant membership, class enrollment, submission, feedback, or teacher review paths. This does not establish whether external clients depend on those routes; external compatibility remains unverified.

## Scope and changes

No production or staging host was accessed. No deploy, migration on a shared database, environment/secret change, DNS/network/firewall/proxy change, or commit was made. The disposable test database and Gate-owned local test resource set were used only for this qualification. Existing Gate 732–735 workspace changes were preserved. Additional local edits in this checkout include a qualification test and test-harness/baseline alignment in the listed test files; application changes were already part of the candidate under qualification.

## Next recommendation

Resolve the two missing test-import modules in their own authorized scope, isolate/reset the process-wide rate limiter between tests, then rerun the complete regression suite. Obtain a separate decision for external-client compatibility before treating undocumented callers as absent.
