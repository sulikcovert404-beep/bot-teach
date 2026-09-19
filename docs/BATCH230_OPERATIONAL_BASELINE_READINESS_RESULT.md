# BATCH230 — Operational Baseline Readiness Result

Date: 2026-09-19
Mode: Read-only
Gate: 230 — Production Readiness Documentation & Operational Baseline

## Verdict

```text
OPERATIONAL_BASELINE_READY
```

No user, subscription, entitlement, migration, worker, provider, DNS, Cloudflare, webhook, environment, or secret mutation was performed.

## Current State Snapshot

| Item | Evidence | Status |
|---|---|---|
| Host | `hamicard`; uptime ~21h50m; load 0.07/0.06/0.05 | AVAILABLE |
| API container | `ai-teacher-staging-api-1`; running; restart count 0; image `staging-api:canonical-0021-candidate` | HEALTHY |
| PostgreSQL | `ai-teacher-staging-db-1`; running; healthy; `pgvector/pgvector:pg16` | HEALTHY |
| Redis | `ai-teacher-staging-redis-1`; running; healthy; `redis:7-alpine` | HEALTHY |
| Local health | `http://127.0.0.1:8000/health` = 200 | PASS |
| Local readiness | `http://127.0.0.1:8000/health/ready` = 200 | PASS |
| Public health | `https://bot.codeshow.ir/health` = 200 | PASS |
| Public readiness | `https://bot.codeshow.ir/health/ready` = 200 | PASS |
| Migration head | readiness JSON reports `20260912_0021` | PASS |
| Mini App | `https://bot.codeshow.ir/mini-app/` = 200 | PASS |
| Cloudflare edge | Public responses carry `Server: cloudflare`, valid `CF-RAY`, dynamic origin responses | HEALTHY |

The Docker API required `sudo`; no secret or environment value was read. The approved runtime image digest remains recorded in the prior qualification package.

## Operational Checklist

### Startup procedure (approval required)

1. Confirm host and release provenance.
2. Confirm canonical compose/config paths and approved image digest without printing secrets.
3. Confirm storage/I/O and Docker health.
4. Use an explicitly approved execution identity.
5. Start only the approved canonical service and verify local then public health/readiness.
6. Abort on provenance mismatch, readiness/migration drift, storage stall, restart loop, OOM, or unexpected 5xx.

No startup action was taken in this Gate.

### Rollback procedure (emergency only)

- Keep old production and old tunnel intact as rollback standby.
- Revert edge traffic only under an explicit incident gate.
- Preserve and verify the recorded pre-cutover backup before any restore.
- Never use `alembic upgrade head` or `alembic stamp`; target an explicit revision only.
- Revalidate health, readiness, webhook destination, and migration lineage after rollback.

No rollback action was taken.

### Incident evidence collection

Capture timestamp, request IDs/CF-RAY, endpoint/status, container state/restart count, Docker and kernel/storage signals, migration head, and redacted logs. Never capture or persist tokens, API keys, webhook secrets, or full environment values.

### Support checklist

- Confirm `/health` and `/health/ready`.
- Confirm API/PostgreSQL/Redis states and restart counts.
- Confirm Cloudflare route and public status.
- Confirm Telegram webhook status without exposing token.
- Confirm Gemini provider status without logging prompt/response or key.
- Escalate only with a redacted evidence bundle.

## Security Baseline

- Secrets remain in the protected environment source; no secret values were printed, copied, exported, or committed.
- Application logs and reports must redact authorization headers, webhook secrets, API keys, initData, and user identifiers where not required.
- Telegram webhook validation is fail-closed: unauthorized public requests return 401; authorized qualification previously returned 200.
- Public boundary exposes health/readiness and approved web surfaces; database and Redis remain internal.
- Entitlement activation remains blocked pending owner-provided test identity, exact plan, feature scope, active window, and audit reason.
- Gemini connectivity is qualified, but entitlement activation and worker enablement remain disabled.

## Activation Dependencies Pending

```text
Test identity: MISSING
Plan: MISSING
Feature scope: MISSING
Active window: MISSING
Audit reason: MISSING
Mutation: NOT AUTHORIZED
```

## Evidence and Limitations

Read-only SSH and public checks completed successfully. Cloudflare tunnel health is established by the current public edge responses and prior tunnel qualification; no Cloudflare dashboard mutation or route change was performed. This report records the current baseline and does not authorize activation or deployment.

## Production Impact

```text
User/subscription mutation: NONE
Database/schema/migration mutation: NONE
Worker/provider activation: NONE
DNS/Cloudflare/webhook mutation: NONE
Production runtime mutation: NONE
```

## Final Status

```yaml
Gate: 230
Verdict: OPERATIONAL_BASELINE_READY
Runtime: HEALTHY
Cloudflare: HEALTHY
Activation: WAITING_FOR_ACTIVATION_INPUT
Commit: HOLD
```
