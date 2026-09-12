# Historical Migration Hardening Exception & Lineage Convergence Record

## 1. Context & Rationale
During historical project execution, the migration history split into two divergent heads from common ancestor `f7a8b9c0d1e2`:
- **Production Lineage**: `f7a8b9c0d1e2` -> `2e0b56730806` (telegram_user_id to BIGINT) -> `20260909_0009` (creates `beta_feedbacks` & `beta_quality_audits`).
- **Staging Lineage**: `f7a8b9c0d1e2` -> `20260907_0008` (file `20260907_0007_beta_feedback_and_quality.py`, creates `beta_feedbacks` & `beta_quality_audits`) -> `0010` through `0019`.

When unifying these branches under canonical dual-parent merge revision `20260912_0020`, Alembic walks DAG order, resulting in an execution path where one branch attempts to re-create tables already existing in the other branch, leading to `relation already exists` errors (`DuplicateTableError`).

## 2. Hardened Historical Migrations
To achieve deterministic, bidirectional convergence without destructive schema rewrites or fake metadata manipulation, an explicit hardening exception was approved:
- `migrations/versions/20260907_0007_beta_feedback_and_quality.py` (Revision: `20260907_0008`):
  Guarded with `sa.inspect` table existence check for `beta_feedbacks` and `beta_quality_audits`.
- `migrations/versions/20260909_0009_feedback_descendant.py` (Revision: `20260909_0009`):
  Guarded with identical `sa.inspect` table existence check.

### Boundary of the Guard:
> [!IMPORTANT]
> The idempotent guard verifies table presence (`if "beta_feedbacks" not in existing_tables:`) to bypass duplicate DDL execution. It assumes catalog parity between identical DDL definitions confirmed via `git diff`. This is NOT an ongoing schema reconciliation mechanism and must not be used for general future migrations.

## 3. Merge Revision: `20260912_0020`
- **Revision ID**: `20260912_0020`
- **Down Revisions**: `("20260909_0009", "20260910_0019")`
- **Operation**: Inspects `users.telegram_user_id` and alters it from `INTEGER` to `BIGINT` only if not already `BIGINT`.
- **Lock Risk & Operational Safeguards**:
  * On Production databases: `telegram_user_id` is ALREADY `BIGINT` (executed in `2e0b56730806`), making `0020` an instantaneous NO-OP requiring NO table rewrite lock.
  * On Staging/Clean databases: `telegram_user_id` is converted to `BIGINT`.
  * Downgrade is explicitly set to `pass` (safe non-destructive no-op).

## 4. Rehearsal Evidence Summary
- **Prod-Lineage Clone (`0009 -> 0020`)**: Succeeded cleanly without duplicate table error. Exit code 0.
- **Staging-Lineage Clone (`0019 -> 0020`)**: Succeeded cleanly, upgraded column to `BIGINT`. Exit code 0.
- **Rollback Strategy**: Full physical/custom dump restoration via `pg_restore` is authoritative. Downgrade via Alembic on merge branches is prohibited.
