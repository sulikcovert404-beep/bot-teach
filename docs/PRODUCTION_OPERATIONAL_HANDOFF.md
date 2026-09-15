# PRODUCTION OPERATIONAL HANDOFF & CLOSURE PACKAGE

## 1. Executive Summary & Verdict
```text
MVP + MIGRATION + PRODUCTION CUTOVER
🟢 OPERATIONALLY CLOSED

Primary Production Host:      95.135.208.167
Active Canonical DB Revision: 20260912_0020
Public Domain & Routing:      https://bot.codeshow.ir
Telegram Webhook Endpoint:    https://bot.codeshow.ir/api/v1/telegram/webhook
Telegram Mini App Canonical:  https://bot.codeshow.ir/mini-app/
Old Production Standby:       107.173.47.76 (Rollback Standby)
Independent External Service: mentor-bot (Untouched & Active)
```

---

## 2. Production Source of Truth & Artifact Fingerprints
- **Git Branch:** `release/prod-lineage-convergence-rc`
- **Git Commit:** `00c8fb71c6f8475280e4bd8e599afcca03c2f43a`
- **Canonical Release Artifact SHA256:**
  `e897693bbafd2390954e26cb75972f612a2e841565d4984f41141329a303e1ee`
- **Target Host Release Path:** `/opt/apps/ai-teacher/releases/canonical-prod-convergence-00c8fb7`

---

## 3. Database State & Post-Cutover Backup
- **Live Migration Head:** `20260912_0020` (dual-lineage convergence head)
- **Alembic Invariant:**
  > [!CAUTION]
  > NEVER run `alembic upgrade head` or `alembic stamp`. Always execute explicit revision target upgrades: `alembic upgrade <revision_id>`.

### Post-Cutover Validated Backup:
- **Location on New Host:** `/var/backups/postgresql/education_post_cutover.dump`
- **Size:** `158KB`
- **Format:** Custom (`pg_dump -Fc`)
- **SHA256:** `8f7a6b4b614959bfb6a1680c8d1b612130fb0ac05f5d857551e8297d9aa16d14`
- **pg_restore Validation:** `PASS` (`470` TOC entries verified)
- **Revision in Backup:** `20260912_0020`

### Pre-Cutover JIT Backup (Preserved on Old Host):
- **Location on Old Host:** `/var/backups/postgresql/20260912T105815Z/education_pre_cutover_jit.dump`
- **SHA256:** `2ed8be33765c88457d2c2eb8a0c65de2f64b61a44c5e769b4cbe9f01a5367723`
- **TOC Count:** `265` entries | State: `0009` baseline preserved.

---

## 4. Production Infrastructure & Active Containers
Host: `95.135.208.167` (Ubuntu 24.04 LTS, Docker Compose managed at `/opt/apps/ai-teacher/deploy/staging`)

| Container Name | Image / Role | Port / Binding | Status |
| :--- | :--- | :--- | :--- |
| `staging-api-1` | `staging-api` (FastAPI / Uvicorn) | `0.0.0.0:8000->8000/tcp` | Active / Healthy |
| `staging-postgres-1` | `pgvector/pgvector:pg16` | `5432/tcp` | Active / Healthy |
| `staging-redis-1` | `redis:7-alpine` | `6379/tcp` | Active / Healthy |

Environment Secrets: `/etc/apps/ai-teacher/staging.env` (Mode: `0600`).

---

## 5. Public Ingress, Routing & Dashboards
Cloudflare Tunnel + Nginx Reverse Proxy routing to `127.0.0.1:8002` (forwarded to `95.135.208.167:8000`).

- **Health Check:** `https://bot.codeshow.ir/health` -> `200 OK` (`{"status":"ok"}`)
- **Readiness Check:** `https://bot.codeshow.ir/health/ready` -> `200 OK` (`{"status":"ready","migration_head":"20260912_0020"}`)
- **Telegram Webhook:** `https://bot.codeshow.ir/api/v1/telegram/webhook` -> `200 OK`
- **Mini App Frontend:** `https://bot.codeshow.ir/mini-app/` -> `200 OK`
- **Student Dashboard:** `https://bot.codeshow.ir/student-dashboard/` -> `200 OK`
- **Teacher Dashboard:** `https://bot.codeshow.ir/teacher-dashboard/` -> `200 OK`
- **Admin Control Center:** `https://bot.codeshow.ir/admin-dashboard/` -> `200 OK`
- **Platform Product Surface:** `https://bot.codeshow.ir/platform/` -> `200 OK`

---

## 6. Post-Cutover Incident RCA & Resolution
- **Incident:** Initial click on Telegram Inline button «🎓 ورود به پنل آموزشی» returned `404 Not Found`.
- **Root Cause:** Environment variable `TELEGRAM_WEB_APP_URL` on the new server was unassigned and fell back to default legacy domain `https://codeshow.ir/mini-app`.
- **Remediation:**
  1. Configured `TELEGRAM_WEB_APP_URL=https://bot.codeshow.ir/mini-app/` in `/etc/apps/ai-teacher/staging.env` and recreated the API container.
  2. Created safe host-scoped HTTP 301 permanent redirect on Old Server for `https://codeshow.ir/mini-app` pointing to `https://bot.codeshow.ir/mini-app/`.
  3. Verified manual button click flow in Telegram Web (`https://web.telegram.org/a/`): /start generated direct Inline Button, click launched Mini App successfully without errors.

---

## 7. Operational Runbook: Rollback Procedure (Emergency Only)
If catastrophic degradation occurs during the rollback window:
1. **Traffic Reversion:**
   On Old Host (`107.173.47.76`), remove proxy pass to new server in `/etc/nginx/sites-available/ai-teacher-forward.conf` and re-enable local service:
   ```bash
   sudo systemctl stop ai-teacher-forward
   sudo systemctl start ai-teacher
   ```
2. **Database Reversion (if writes diverged):**
   ```bash
   sudo -u postgres dropdb education
   sudo -u postgres createdb education
   sudo -u postgres pg_restore -d education /var/backups/postgresql/20260912T105815Z/education_pre_cutover_jit.dump
   ```
3. **Webhook Reversion:**
   Verify `getWebhookInfo` points back to active Old Production.
4. **Validation:**
   Verify `/health` and `/health/ready` return 200 with migration head `20260909_0009`.

---

## 8. Preserved Boundaries & Invariants
- **mentor-bot:** Runs independently on `107.173.47.76` (`/etc/systemd/system/mentor-bot.service`). NEVER modify, restart or touch this service.
- **Old Host Lifecycle:** Must remain intact in `ROLLBACK STANDBY` mode until formal notice from management. Do not delete or upgrade OS packages.

## Codex Read-only Post-Edge Verification (2026-09-12)

- SSH to `95.135.208.167` succeeded. API, PostgreSQL, and Redis containers were running; PostgreSQL and Redis reported healthy, API restart count was zero.
- Local origin verification: `http://127.0.0.1:8000/health` and `/health/ready` returned 200; readiness reported migration head `20260912_0020`.
- Public verification: `bot.codeshow.ir` returned 200 for `/health`, `/health/ready`, `/mini-app/`, `/student-dashboard/`, `/teacher-dashboard/`, `/admin-dashboard/`, and `/platform/`.
- Cloudflare DNS inspection showed `bot.codeshow.ir` as a Tunnel record targeting `ai-teacher-new`; `cutover-check.codeshow.ir` remains present and is pending approved removal.
- Backup SHA256 matched the recorded value. Host-level `pg_restore` is unavailable; no destructive backup operation was attempted. Existing recorded `pg_restore --list` evidence remains unchanged.
- No production mutation, migration, deploy, restart, route change, or mentor-bot action was performed by this verification.
