# Artifact Deployment Gate Preparation

Status: READY / BLOCKED — preparation only

## Current production evidence

- Host: `95.135.208.167` (`srv20708.deluxhost.net`)
- Database revision: `20260912_0020`
- Running API image: `sha256:f13e836c7500fb84eb856bbbd70f7e2ff4fed42c46a254b423c6faab72b16315`
- Current image migration graph: ends at `20260910_0019`; it cannot resolve `20260912_0020`.
- API, PostgreSQL, and Redis were healthy during the read-only preflight.

## Canonical artifact

- Path: `/opt/apps/ai-teacher/releases/canonical-release-prod-convergence-00c8fb7.tar.gz`
- SHA256: `e897693bbafd2390954e26cb75972f612a2e841565d4984f41141329a303e1ee`
- Contains `20260912_0020_merge_production_staging_lineage.py` with parents `20260909_0009` and `20260910_0019`.
- Migration `20260912_0021` is not part of this artifact.

## Rollback references

- Fresh backup: `/var/backups/postgresql/education_preflight_20260914T152203Z.dump`
- Backup SHA256: `2c25647e72a2d44cb5ef14f484cc05d63795dd9d20770828f59bb40262b6f6ef`
- `pg_restore --list`: PASS
- Existing running image remains the rollback reference; no replacement has occurred.

## Planned sequence (requires a separate deployment gate)

1. Re-verify artifact SHA and provenance.
2. Obtain explicit deployment authorization.
3. Deploy the canonical artifact compatible with DB revision `20260912_0020`.
4. Verify image migration graph and application startup before any migration decision.
5. Re-run `/health`, `/health/ready`, dashboard smoke routes, and `alembic current`.
6. Only after a new decision gate, consider `0020 → 0021`.

## Prohibited during preparation

No deploy, image pull/replacement, container restart, compose change, migration, stamp, downgrade, database mutation, environment change, credential change, or Cloudflare/webhook change.

Production mutation in this preparation: **NONE**.
