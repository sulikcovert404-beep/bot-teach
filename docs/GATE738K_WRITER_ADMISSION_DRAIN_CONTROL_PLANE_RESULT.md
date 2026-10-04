# Gate738K — Writer Admission and Drain Control Plane

Date: 2026-10-04  
Verdict: `GATE738K_LOCAL_QUALIFICATION_PASS_WITH_HOST_IPV6_LIMITATION`

## Scope and provenance

This qualification used the local workspace at `e4140c4d55a2943c53ecc187a28729663073d48d`, a local disposable PostgreSQL 16/pgvector container, synthetic users, and Gate738K-only Docker resources. Revision `20261004_0032` was applied only to the two Gate-owned disposable databases. No shared, staging, or production service was contacted or changed. No deployment, image build, secret read, DNS/firewall operation, or external ingress was performed.

The API runtime used the pre-existing local image `ai-teacher-pilot-api:gate342-observability` (image ID `sha256:9cf0076fc8eb35fb1d9e85aa510ed7c6aa72dc6ee8aff48b24fd84f7b6fb7ac5`) with the current workspace `app/` and Gate test harness bind-mounted read-only. This is a source-mounted disposable rehearsal, not an immutable release artifact or deployment qualification.

The only running resources used or created for this rehearsal were named `codex-gate738k-*`, on Gate-owned networks. PostgreSQL was published only at `127.0.0.1:18574`; the synthetic ingress was published only at `127.0.0.1:18572` and `[::1]:18572`. Old/candidate API containers had no host-published ports. Other project containers and resources were left untouched.

## Control-plane implementation

- Added `20261004_0032` (`20261003_0031` parent) with persistent `SERVING → DRAINING → FENCED` generation state. Downgrade is deliberately prohibited.
- Admission takes a transaction-held `FOR SHARE` lock on the generation row. The operator transition takes `FOR UPDATE`, so it waits for admitted transactions; the durable state change serializes queued admissions. PostgreSQL backend application names identify generation and instance before lock waits, allowing independent observation through `pg_stat_activity`.
- A database trigger guards row writes across ordinary and partitioned public tables, assigning pre-control-plane writers to the durable `legacy` generation. The control table and migration bookkeeping tables are excluded from business-write triggers. The app runtime receives function execution only; it cannot update the control table.
- The SQLAlchemy engine boundary admits ORM and textual DML before execution and records process metrics. Metrics are diagnostic; database activity and persistent generation state are authoritative for the drain decision. Metrics carry generation/instance/count and duration only, without SQL text or payloads.
- Health/readiness and metric wiring use the writer configuration; admission remains disabled by default. Enabled identities are constrained to non-secret generation/instance identifiers.

## Verification evidence

The disposable databases `ait_gate738k` and `ait_gate738k_http` were freshly created and migrated from source to `20261004_0032`. HTTP qualification used only synthetic `users` rows. The disposable `app_runtime` role had admission-function `EXECUTE`, `users(id)` read and `users(username)` update, and no `UPDATE` on `ai_teacher_writer_generation_state`.

PostgreSQL integration tests passed: `3 passed`. The drain/race test was then repeated five times: all five passed. The tests exercised transaction-held writes, observed active generation/instance counts, queued old writers, independent candidate writes, durable `DRAINING`/`FENCED` behavior, rejection of writes after those committed states, direct SQL without the new application hook, and database-backend termination. The backend-termination case verified the synthetic business-row change rolled back and the DB observer returned to zero active writers.

The end-to-end local HTTP topology rehearsal passed:

- IPv4 ingress initially reached old; after the route switch, readiness and writes reached candidate.
- The old API had no published host port. The ingress was the sole published service, bound to loopback only.
- The database concurrency test held an admitted old business-row update open while the operator requested drain; the transition did not complete until the old transaction resolved. After committed `DRAINING`, a direct old-backend write returned HTTP 500 and left the synthetic row unchanged, including after restarting the old container.
- After committed `FENCED`, direct old-backend writes still returned HTTP 500, including after another restart. Candidate writes through ingress continued returning HTTP 200.
- Database observation reported zero active legacy writers after draining/fencing.
- Ingress health over IPv6 from within the Docker network returned HTTP 200. A host request to `[::1]:18572` timed out despite Docker showing the loopback port mapping. Treat host-side IPv6 forwarding as unverified/blocked by this local Docker Desktop environment; this rehearsal does not qualify public IPv6 exposure.

Focused regression tests passed: `51 passed, 1 skipped` on the related API/health/metrics/auth/teacher/admin/submission/writer set before the final strengthening of the DB race assertions; after that strengthening, the final writer integration suite passed `3 passed`, the race test passed five additional consecutive runs, and configuration/health/migration qualification tests passed `10 passed`. `py_compile`, focused Ruff checks, and `git diff --check` passed. The full repository regression suite was not run.

## Limits and next decision

This proves the local control plane and the tested synthetic routes, not exhaustive coverage of every possible database client or untested raw connection path. Production/staging adoption would require a separate approved gate for migration, release artifact construction, complete runtime writer identity/environment configuration, operator monitoring privileges, deployment order, and rollback. The ingress test harness is synthetic and loopback-only. Host IPv6 forwarding remains unqualified.

No commit was created. The worktree contains pre-existing uncommitted Gate731N–738J work; it was preserved.
