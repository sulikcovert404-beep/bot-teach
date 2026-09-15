# TECHNICAL SENSITIVE REVIEW: PRODUCTION MIGRATION LINEAGE CONVERGENCE
## Review Target: Dual-Parent Merge Revision 20260912_0020 (0009 & 0019 -> 0020)

### 1. Problem Statement
The codebase developed two separate migration lineages originating from common ancestor `f7a8b9c0d1e2`:
- **Production Lineage:**
  `f7a8b9c0d1e2` -> `2e0b56730806` (ALTER TABLE users ALTER COLUMN telegram_user_id TYPE BIGINT) -> `20260909_0009` (CREATE TABLE beta_feedbacks, CREATE TABLE beta_quality_audits)
- **Staging Lineage:**
  `f7a8b9c0d1e2` -> `20260907_0008` (CREATE TABLE beta_feedbacks, CREATE TABLE beta_quality_audits) -> `0010` through `0019` (content generation, schools, assignments, RLS, school_admin_memberships).

### 2. Critical Overlap & Convergence Finding
Alembic resolves multiple parents by walking all unapplied ancestors when upgrading to a merge revision:
- If a Production database at `20260909_0009` executes `alembic upgrade 20260912_0020`, Alembic will attempt to apply the missing branch: `20260907_0008` through `20260910_0019`.
- However, `20260907_0008` attempts to execute:
  `op.create_table("beta_feedbacks", ...)` and `op.create_table("beta_quality_audits", ...)`
  which **ALREADY EXIST** on the production database from revision `20260909_0009`!
- Therefore, a direct upgrade on a production clone without compatibility guards will fail with:
  `duplicate table error: relation "beta_feedbacks" already exists`.

### 3. Review Questions for Independent Reviewer (Claude 3.5 Sonnet):
1. **Safety of Dual-Parent Merge from 0009:**
   Given the identical duplicate tables created in `0008` vs `0009`, how should the migration DAG handle this collision cleanly without mutating existing historical migration files?
2. **Compatibility Strategy:**
   Options:
   - A: Make table creation in `0008` / `0009` conditional or add an idempotent pre-check.
   - B: Create a synthetic bridge revision that marks `0008` satisfied or unifies the fork before 0010.
   - C: Use schema reflection / IF NOT EXISTS pattern.
3. **Data Integrity & Column Types:**
   Does converting `telegram_user_id` to BIGINT risk any index corruption or locking on PostgreSQL under production load?
4. **Rollback Strategy:**
   Is full physical dump/restore strictly superior to Alembic downgrade for this cutover?
