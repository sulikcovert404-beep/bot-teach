# Gate 176 — Controlled Secret Injection Model Result

**Target:** `antigravity@92.118.190.101` (`hamicard`)
**Scope:** Secret storage/injection model and leakage controls only
**Mutation status:** NONE
**Gate commit:** HOLD

## Recommended model

Use an owner-managed, root-controlled environment file outside the repository for the first controlled deployment, with Docker Compose receiving it through an explicit `--env-file` path. The canonical path is:

`/etc/apps/ai-teacher/staging.env`

This is a design decision only; the file was not created and no secret was read or transferred. The file must be owned by `root:root`, mode `0600`, excluded from all Git trees and backup exports unless encrypted, and supplied only to the approved Compose project. The later secret-injection gate must verify that Compose does not expose it through image layers, command arguments, logs, or unrelated projects.

A system secret manager or Docker secrets backend remains an acceptable future replacement, but the current frozen Compose contract uses variable interpolation and `env_file`; introducing a new secret backend would require a separate implementation gate and qualification. No provider secret is to be pasted into chat.

## Secret categories and boundaries

| Category | Owner | Location/model | Rotation | Access boundary |
|---|---|---|---|---|
| PostgreSQL bootstrap/migration credentials | platform owner / root | `/etc/apps/ai-teacher/staging.env`; migration service only | rotate after bootstrap and on incident | `migrate`/DB owner only; never API container |
| API runtime DB credential | platform owner / root | same file or secret-manager entry | controlled rotation with readiness check | API `app_runtime` only; `NOSUPERUSER`, `NOBYPASSRLS` |
| Redis credential (if enabled) | platform owner / root | same file or secret-manager entry | incident/periodic rotation | project-local Redis network only |
| Telegram bot token/webhook secret | platform owner | same file/secret manager | BotFather rotation or incident | API webhook path only; never logs/reports |
| Gemini/provider API keys | platform owner | same file/secret manager | provider rotation/incident | provider adapter only; activation is a separate gate |
| Payment provider credentials | platform owner | same file/secret manager | provider rotation/incident | payment adapter/webhook only |
| TLS/edge credentials | edge owner | Cloudflare/approved edge secret store | certificate/key rotation | edge layer only; not copied to app source |

## Injection controls

- Preflight confirms the target file path, owner, mode, and checksum metadata without printing values.
- Compose is invoked with the explicit project file and `/etc/apps/ai-teacher/staging.env`; no shell command contains a secret value.
- The configuration file is never copied into `/opt/apps/ai-teacher`, source archives, Docker build context, Git, or images.
- Runtime variables are inspected only by key name and presence/length in a controlled validation command; values are redacted.
- The API runtime receives only required variables. Migration-only credentials are not inherited by the API service.
- Rotation is staged as write-new/validate/readiness/retire-old, with rollback to the previous file only under a separate incident gate.

## Leakage prevention checklist

- Frozen tag `.gitignore` covers `.env`, `*.env`, `*.pem`, `*.key`, and known local/runtime artifacts.
- `.dockerignore` excludes `.env` and Git/cache material from image context.
- Secret scans must run on source archive, Compose config rendering, container metadata, logs, and reports; findings fail closed.
- No secret in chat, ticket, commit, shell history, process arguments, Dockerfile layer, backup, or screenshot.
- Backups of the configuration file are disabled by default; if required, encrypt and access-control them separately.
- File and directory permissions are checked before any application start; cross-project ownership or mounts fail closed.

## Out of scope / not performed

No secret was received, pasted, generated, copied, or read. No real `.env` was created. No API key, certificate, database credential, application start, Compose startup, DB connection, migration, DNS, Cloudflare, webhook, or edge mutation occurred.

## Verdict

`SECRET_INJECTION_READY`

The model is ready for a separately approved first secret-injection gate. Gate 176 commit remains HOLD.
