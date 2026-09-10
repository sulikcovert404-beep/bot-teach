# STAGING ARTIFACT PARITY + REPOSITORY SYNC REPORT

Date: 2026-09-10

## Verdict
- Migration lineage: unchanged; no migration executed against live staging.
- API and migration images rebuilt from workspace commit e2d231f.
- Migration file 20260909_0015_assignment_persistence.py present in both rebuilt images.
- Image heads: 20260909_0009, 20260909_0015.
- Live readiness: HTTP 200, migration head 20260909_0015.
- Docker services: API, PostgreSQL, Redis healthy.
- Full regression: 868 passed, 2 warnings.
- Secret scan: PASS.
- Repository sync: fast-forward 066a5f2 -> e2d231f.
- Production: unchanged.

## Active image digests
- API image digest: sha256:c34fdb0d7f6279c218dee543bf38105dc07a7ed1cbb0f4f898f9931e479b321d
- Migration image digest: sha256:770144d10df693715344fe0f633cd3cafc1c513729e1400e303a53696f030eae

## Notes
The orphan stagingwave-api-pub container was not removed. No schema, migration, webhook, or production changes were performed.

## Follow-up verification (2026-09-10)
- API container contains migration `20260909_0015_assignment_persistence.py`.
- Read-only Alembic current inside the running API container: `20260909_0015`.
- Read-only Alembic heads inside the running API container: `20260909_0009` and `20260909_0015`; `20260909_0014` is not a head.
- `/health/ready`: HTTP 200 with `migration_head=20260909_0015`.
- `docker compose -p stagingwave ps`: API, PostgreSQL, and Redis healthy.
- Focused authorization/assignment/health regression: 16 passed, 2 warnings.
- `git rev-list --left-right --count origin/master...HEAD`: `0 0` (no remote divergence).
