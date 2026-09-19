# Gate 175 — Environment Configuration Preparation Result

**Target:** `antigravity@92.118.190.101` (`hamicard`)
**Scope:** Configuration-boundary inventory and preparation only
**Mutation status:** NONE
**Gate commit:** HOLD

## Environment boundary

The canonical runtime configuration boundary is `/etc/apps/ai-teacher/`. The directory was created in Gate 169 and is owned by `ai-teacher:ai-teacher` with mode `0750`. Gate 175 did not create a runtime `.env`, copy secrets, or alter permissions. The source checkout remains under `/opt/apps/ai-teacher/release-local-rc-2026-09-17`; configuration is intentionally outside the source tree.

Recommended eventual file policy (requires a separate secret-injection gate): root/approved secret-manager ownership, mode `0600`, excluded from Git and backup exports unless encrypted, and mounted/read by the application only through the approved Compose `env_file`/secret mechanism.

## Template inventory

Inventory was taken from the frozen tag `local-rc-2026-09-17` without loading any real environment value.

| Variable | Classification | Runtime dependency / control |
|---|---|---|
| `APP_ENV` | required | Must be `production` for production validation; enables strict checks. |
| `APP_NAME` | optional | Application label. |
| `LOG_LEVEL` | optional | Bounded production logging level. |
| `DATABASE_URL` | secret-backed required | API runtime connection; must use `app_runtime`, never the migration owner. |
| `POSTGRES_PASSWORD` | secret-backed required | Database bootstrap/migration identity only; never in API runtime. |
| `APP_RUNTIME_PASSWORD` | secret-backed required | Least-privilege API DB identity. |
| `EXPECTED_MIGRATION_HEAD` | required non-secret | Must be explicitly pinned and separately approved; never `alembic upgrade head`. |
| `TELEGRAM_BOT_TOKEN` | secret-backed required | Telegram integration. |
| `TELEGRAM_WEBHOOK_SECRET` | secret-backed required | Webhook validation. |
| `PAYMENT_WEBHOOK_SECRET` | secret-backed required | Payment webhook validation. |
| `PAYMENT_PROVIDER_URL` | optional external dependency | Must be HTTPS when configured. |
| `PAYMENT_PROVIDER_API_KEY` | conditional secret | Required only when payment provider URL is configured. |
| `GEMINI_API_KEY` | secret-backed required | Dynamic AI provider; provider activation is a separate gate. |
| `AI_DEFAULT_MODEL` | optional/approved value | Must be reviewed against provider availability before activation. |
| `JWT_SECRET` | secret-backed required | At least 32 characters in production. |
| `RATE_LIMIT_REQUESTS` | optional | Runtime protection. |
| `RATE_LIMIT_WINDOW_SECONDS` | optional | Runtime protection window. |
| `REDIS_URL` | required | Internal project Redis only; no shared cache endpoint. |
| `CORS_ALLOWED_ORIGINS` | required for edge | HTTPS origins only in production; wildcard is rejected. |

The template also contains the frozen tag's migration expectation (`20260912_0021`). This is metadata, not evidence that the new server has a database or that migration 0021 is approved. No migration or database was created.

## Additional code-level dependency findings

- `telegram_web_app_url` has a safe code default but is not listed in `.env.example`; the eventual configuration gate must decide whether to expose an explicit canonical value.
- PDF extraction limits (`PDF_MAX_PAGES`, `PDF_EXTRACTION_TIMEOUT_SECONDS`) are optional process-level controls read by the admin-content route and are not in the template.
- Settings load `.env` and, when present, `/run/secrets`; the future injection gate must choose one approved source and prohibit duplicate/conflicting values.
- Production validation rejects placeholder values, missing required secrets, non-HTTPS payment/CORS origins, and wildcard CORS.

## External dependency map

- **PostgreSQL:** `DATABASE_URL`, `POSTGRES_PASSWORD`, `APP_RUNTIME_PASSWORD`; project-local DB service and separately approved migration owner.
- **Redis:** `REDIS_URL`; project-local Redis service/network only.
- **Telegram:** bot token, webhook secret, and canonical WebApp URL; webhook/edge changes require a separate gate.
- **Gemini:** API key and approved model; provider credential remains outside this gate.
- **Payments:** optional URL plus conditional API key and webhook secret.
- **Domain/edge:** CORS origins and WebApp URL; Cloudflare, DNS, TLS, and reverse proxy remain unconfigured and out of scope.

## Secret boundary

Secrets must be provisioned by the owner-approved secret manager or controlled `0600` configuration file on the server. They must not be placed in source, Git history, Dockerfile layers, command arguments, reports, logs, or unencrypted backups. Gate 175 read no real secret and transferred none.

## Prohibited actions in Gate 175

No real `.env` creation, secret/API-key/certificate transfer, database credential creation, application start, Compose startup, migration, DNS/Cloudflare change, or production edge change was performed.

## Verdict

`ENV_CONFIGURATION_READY`

Configuration structure and dependency boundaries are ready for a separate, explicitly approved secret-injection gate. Gate 175 commit remains HOLD.
