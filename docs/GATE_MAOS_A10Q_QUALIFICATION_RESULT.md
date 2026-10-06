# GateMAOS-A10Q — Qualification Completion Result

STATUS: `SCHEMA_REPAIR_REQUIRED`

FINAL VERDICT: `A10Q_BLOCKED`

No commit, push, CI run, shared staging access, production access, deployment, provider call, or external effect occurred.

## Source identity and scope

- Worktree: `D:\project\ai-teacher-maos-a5o`
- Branch: `codex/gate-maos-a5o`
- Parent/source: `29edcfa3fc34c509eb0342ce84a8a16530e596a8`
- A10 migration revision: `20261006_0034`
- Declared parent: `20261004_0033`
- Migration SHA-256 during A10Q: `eccf29c4ecaab2be7d725720c80bd46c7ad7834a82658d8878579bb182d29b3a`
- Migration Git blob: `bb611a3fc33a0cb18d673702851a1081980382e1`
- Migration size: `19,987` bytes
- These match the captured pre-A10Q migration identity; migration 0034 was not edited.
- Frozen base manifest, Kernel V1 extension, and Authority V1 extension were not edited.

## Completed A10Q qualification work

- Added a separate exact A10 source extension for only `migrations/versions/20261006_0034_maos_durable_foundation.py`, bound to the frozen base SHA/blob and the migration's exact SHA-256, Git blob, and size.
- Extended the source-closure validator to reject missing, extra, duplicate, overlapping, altered, wrong-base, and test-only paths. The Docker copy source is verified as `COPY migrations ./migrations`.
- Effective candidate source closure is exactly `426` paths: frozen base `409` + Kernel V1 `13` + Authority V1 `3` + A10 `1`.
- Canonical environment: Linux x86_64, CPython `3.12.15`; exact lock SHA-256 `4891ea0d685df0c127aa0d79991e451541b886f1a345e81f64ce6af6d8d528ac`; installed using `pip --require-hashes`.
- Mypy: baseline `579`, current `579`, new `0`, resolved `0`.
- Canonical focused tests covering A10 PostgreSQL fixture, source provenance, Docker copy closure, health, migration graph, and legacy harness: `50 passed`.
- Ruff and py_compile passed for the provenance validator/tests before the real-lineage run; `git diff --check` passed at that point.

## Real migration lineage and blocking defect

A fresh disposable `pgvector/pgvector:pg16` cluster was used because the vanilla `postgres:16` image lacked the repository's required `vector` extension. The A10Q cluster is named `maos-a10q-lineage-pgvector16`, bound to loopback port `18580`, and attached only to the task-specific `maos-a10q-20261006` Docker network.

Using actual repository migrations with explicit revision targets, the database successfully reached `20260921_0022`, `20261003_0029`, `20261004_0032`, `20261003_0030`, `20261003_0031`, and `20261004_0033`. The repository backfill validator ran on the empty disposable database and reported zero submissions, revisions, reviews, or errors. Disposable writer-state prerequisites were set only in that isolated database; this does not claim Gate738P hard-crash qualification.

The explicit `alembic upgrade 20261006_0034` failed at migration line 305 while creating the MAOS writer-fence triggers:

```text
permission denied for function public.gate738k_guard_writer
```

The migration executes `SET LOCAL ROLE maos_audit_owner` before creating those triggers. The actual predecessor migration `20261004_0032` revokes `EXECUTE` on `public.gate738k_guard_writer()` from `PUBLIC` and does not grant it to `maos_audit_owner`. The role needed for trigger creation therefore lacks the required function permission.

Post-failure read-only checks confirmed:

- `alembic_version = 20261004_0033`
- `maos` schema absent
- `maos_audit_owner` absent
- no partial 0034 schema persisted
- migration 0034 bytes and Git blob remain unchanged

Because A10Q is qualification-only and freezes migration semantics, no grant or migration repair was attempted. The A10Q qualification stopped here as required.

## Readiness alignment incompatibility

The current runtime default in `app/api/routes/health.py` still expects `20261004_0033`. That file is already present in the frozen 409-path base manifest with SHA-256 `f334e76d1f488875727eee5f9fc1f8ed8cbb90efa3aa3f997f916254ecb43fc2`. Updating the runtime head to `20261006_0034` would change a base-pinned path, while the A10Q rules prohibit editing the frozen base and prohibit overlapping additive extensions. Test-only current-head expectations were aligned by the A10 implementation, but the runtime readiness fallback cannot be aligned within the stated frozen-manifest constraints. No production env or runtime file was changed.

This incompatibility is separately unresolved; it is not represented as completed readiness alignment.

## Not completed because A10Q stopped on the defect

- 0034 migration on the actual repository predecessor path: failed as described above.
- Post-migration A10 security behavior on that real path: not run.
- Representative MAOS data, custom-format dump, and second-instance restore: not run.
- Full canonical pytest suite: not run after the schema defect.
- Runtime readiness alignment to 0034: blocked by the frozen base-manifest overlap described above.

The earlier synthetic-0033 PG16 test still passes, but it does not override the real-lineage failure.

## Files changed during A10Q

- `scripts/gate738ad_maos_source_extension.py`
- `tests/test_gate738ad_maos_source_extension.py`
- `tests/test_maos_a10_persistence_postgres.py` (test-target selection for a uniquely named A10Q disposable container)
- `docs/GATE738AD_MAOS_A10_PERSISTENCE_SOURCE_EXTENSION.json`
- `docs/GATE_MAOS_A10Q_QUALIFICATION_RESULT.md`

Pre-existing A10 implementation changes to the three current-head tests and the A10 report remain as they were at A10Q entry. A8 Authority V1 and Kernel V1 files remain unchanged.

## Required Commander decision

Issue a separate narrow repair/qualification Gate for the missing `maos_audit_owner` permission required to create the writer-fence triggers, and resolve how readiness can target 0034 without invalidating the frozen candidate manifest. Do not treat A10Q as passed, and do not commit or push until the repair path and artifact provenance are separately authorized and qualified.

Mutations were limited to authorized local provenance/test/readiness-contract work and two task-namespaced disposable PostgreSQL 16 clusters. No other container, network, volume, database, or project was changed.
