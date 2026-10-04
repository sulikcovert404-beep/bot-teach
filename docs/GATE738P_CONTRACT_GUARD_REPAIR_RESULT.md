# Gate738P — Contract Guard Repair and Crash-Safe Qualification

## Verdict

`CONTRACT_GUARD_REPAIRED_AND_DISPOSABLE_QUALIFICATION_PASSED`

The Gate738P requirements passed on a fresh, local-only PostgreSQL 16/pgvector database and a newly built local candidate image. No staging or production resource was contacted or changed; no image was pushed and no commit was created.

## Repaired boundaries

- Writer generation is derived from PostgreSQL `session_user` and a database-owned generation-to-login-role map. The candidate role is distinct from `app_runtime`; `app_runtime` cannot assume that candidate role. Caller-controlled GUCs and `application_name` are observability metadata only.
- Migration ancestry is now one ordered path: `20260921_0022 → 20261003_0024 → 0025 → 0026 → 0027 → 0028 → 0029 → 20261004_0032 → 20261003_0030 → 0031 → 20261004_0033`. There is one Alembic head.
- The runner supports exact target `0029` (expand), `0032` (control plane), explicit drain and fence actions, and the exact contract targets `0030`, `0031`, and `0033`. It has no `upgrade head` path. Candidate health must return HTTP 200, `status=ready`, the exact pre-target revision, and a verified candidate DB identity.
- The contract guard fails closed unless the OLD role is durably FENCED, the candidate role is registered and SERVING, the candidate has a live DB session, database activity visibility is complete, no OLD transaction remains, no other generation is SERVING/DRAINING, and runtime privilege/ACL checks pass.
- Contract completion also requires a structured hard-crash evidence file produced by the disposable qualification harness.

## Qualification evidence

- PostgreSQL-backed contract/impersonation matrix: **11 passed**. It rejected legacy SERVING and DRAINING, absent or fenced candidate, a second admission-capable generation, an active OLD transaction, `PUBLIC` execute, and `app_runtime` presenting candidate-looking `application_name`; the valid distinct candidate passed.
- Gate738K drain/restart/direct-SQL regression with separate login identities: **3 passed**.
- Hard crash: a real OLD writer container held an uncommitted write while the operator drain waited on its database lock. Docker hard-killed OLD with exit code `137`; the write rolled back; drain completed; OLD restart writes were denied in DRAINING and again after the durable FENCED transition; the candidate API remained ready and an application-factory candidate write succeeded.
- On that disposable database, the real empty-data backfill validator passed, then the explicit `0029 → 0032 → 0030 → 0031 → 0033` sequence completed. Final head was `20261004_0033`; OLD remained FENCED, candidate remained SERVING, and candidate readiness returned HTTP 200.
- Full workspace suite with Gate738P and Gate738K PostgreSQL cases enabled: **1017 passed, 11 skipped**. One existing Starlette/httpx deprecation warning remains.
- Ruff on all Gate738P-touched Python files and the affected health/configuration/migration tests: passed. `py_compile` passed for the staged runner, migrations, and crash harness. `git diff --check` passed.
- Local candidate image: `codex-gate738p-candidate-20261004:latest`, image/manifest digest `sha256:d3c95ece976ca6425b5fc5ee6b2b93cb73f0d1bea868e264de6fa0c0ef318fe2`, Linux/amd64. The pinned base image is recorded in the manifest. No registry push occurred.
- Source hashes for 407 artifact/context files are recorded in [the candidate manifest](GATE738P_CANDIDATE_MANIFEST.json); its SHA256 is `a51a830f0f435e0e00dca83d8d133191324d9304f2cfb9b1a2f347ff9ece26a1`. The actual hard-crash assertions are in [the evidence record](GATE738P_HARD_CRASH_EVIDENCE.json).

## Gate738H harness follow-up

The standalone legacy `tests/gate738h_qualification.py` was also attempted. Its pre-contract data/backfill work advanced to the old direct `alembic upgrade 20261003_0030` call, which the repaired chain correctly refused because that harness does not provision/pass the new distinct candidate DB identity or run the required `0032` control plane and drain/fence stages. It failed closed before contract DDL and did not corrupt its disposable database. This legacy orchestration harness is **not counted as passed**; its sequence needs updating if its full race/compatibility suite remains a required Gate738P acceptance item. Gate738P’s own populated-requirement matrix and hard-crash/explicit-contract sequence did pass, and the full pytest suite passed.

## Safety and cleanup

No migration, database write, deploy, runtime restart, image push, secret change, or other project operation occurred outside the named disposable Gate738P resources. The exact leftover database created by the attempted Gate738H harness, the Gate738P-only PostgreSQL container, and its named volume were removed. No wildcard, prune, or shared-resource cleanup was used. The candidate image remains local for review or a later Gate.

Production remains **NO-GO**. A real production backup restore has not been verified, and IPv6 ingress qualification remains unverified/environment-dependent.
