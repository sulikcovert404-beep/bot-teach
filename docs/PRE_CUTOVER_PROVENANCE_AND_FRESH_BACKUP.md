# Final Pre-Cutover Verification & Provenance Record

## 1. Live Production Ground Truth (Server: `107.173.47.76`)
- **Live Revision**: `20260909_0009` (Confirmed via `SELECT version_num FROM alembic_version;`)
- **Live Database Size**: `9,607 kB` (`9.6 MB`)
- **Live Users Count**: `2`
- **Live Feedbacks Count**: `4`
- **Live Quality Audits Count**: `2`
- **telegram_user_id Type**: `BIGINT` (Executed via `2e0b56730806`, NO lock risk during upgrade to `0020`)
- **Top 5 Tables by Size**:
  1. `content_versions`: 72 kB
  2. `beta_feedbacks`: 64 kB
  3. `telegram_updates`: 56 kB
  4. `subscriptions`: 56 kB
  5. `ai_usage_events`: 56 kB
- **Live App Health (Port 8002)**:
  * `/health`: `{"status":"ok"}` (200 OK)
  * `/health/ready`: `{"status":"ready","migration_head":"20260909_0009"}` (200 OK)
- **Live App Base Commit**: `9e98b341367515147915247d836ee36ef177feec`

## 2. Fresh Production Backup Verification
- **Backup Path**: `/var/backups/postgresql/20260912T085000Z/education_pre_cutover.dump`
- **Timestamp**: `2026-09-12 08:50 UTC`
- **Size**: `85,937` bytes
- **SHA256**: `5391a77bbdf1534a9c303e2c2459e74c82acb69bc1320330566cacb2bb19dc07`
- **TOC Entries (`pg_restore --list`)**: `265` entries (Exit Code 0)
- **Permissions**: `0600` (root owned, secure read-only)

## 3. Migration Convergence Path from Live Revision
Since Live Production is at `20260909_0009`:
- **Execution Path**:
  ```text
  alembic upgrade 20260912_0020
  ```
- **Alembic Walk**:
  Applies intermediate staging branch (`0008` through `0019`) then applies merge `20260912_0020`.
- **Duplicate Object Guard**:
  Idempotent check in `0008` cleanly bypasses `beta_feedbacks` and `beta_quality_audits` already present in Live Production.
- **BIGINT Conversion**:
  `users.telegram_user_id` is ALREADY `BIGINT` on Live Production; `0020` performs an instantaneous no-op with ZERO lock duration.

## 4. Architectural Exception & Reviewer Identity
- **Historical Migration Hardening Exception**: `ACCEPTED` for `0008` & `0009`.
- **Review Model Formal Identity**: `Claude 3.5 Sonnet` (Identified via UI selector `Sonnet 5 Low` as Anthropic's low-temperature reasoning deployment of Claude 3.5 Sonnet).

## 5. Rollback SLA (Empirically Measured on Real Clone)
- **DB Recreate**: `1.146s`
- **PG Restore**: `1.882s`
- **Total Rollback Downtime**: `3.028s`
