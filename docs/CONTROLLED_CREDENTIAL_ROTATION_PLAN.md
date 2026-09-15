# Controlled Credential Rotation Plan

Status: PLAN ONLY — NOT EXECUTED

## Credential Order

1. Gemini/API provider keys: provision replacement and validate through a controlled provider gate.
2. JWT/session secret: coordinate session invalidation and controlled restart.
3. Telegram webhook secret: provision replacement, update webhook secret atomically, verify delivery.
4. Redis credentials/URL: provision replacement and restart only the dependent API after connectivity verification.
5. Database URL/password: create replacement credentials, verify least privilege, then rotate with rollback coverage.
6. Telegram bot token: rotate only with BotFather owner approval, then re-register webhook and run Telegram E2E.

The order is provisional and must be confirmed against the actual provider and deployment dependencies before execution.

## Impact Matrix

| Credential class | Consumers | Runtime impact | Restart | Downtime risk |
|---|---|---|---|---|
| Gemini/API | provider adapter/config | provider calls only | likely API restart | low, fallback dependent |
| JWT/session | auth/session validation | existing sessions may invalidate | API restart | medium |
| Telegram webhook secret | webhook validation | inbound webhook auth | API/config plus webhook update | medium |
| Redis | cache/session/rate limits | cache and session connectivity | API restart | medium |
| Database | SQLAlchemy/database layer | all persistence | API and DB credential coordination | high |
| Telegram bot token | Telegram adapter/webhook | bot send/receive | webhook re-registration | high |

## Safety Checks

- No dual-secret support was assumed; verify before execution.
- No migration is required by the plan.
- Webhook re-registration is required only for webhook secret or bot-token rotation.
- Session invalidation is expected for JWT rotation and must be announced/verified.
- Rotation must be staged with pre-rotation backup and post-change health/readiness checks.

## Rollback Strategy

Use provider-specific rollback mechanisms without printing or retaining old values in reports. Maintain an encrypted owner-controlled recovery path outside git, then restore the previous configuration only if health/readiness, dependency checks, or Telegram E2E fail. Verify `/health`, `/health/ready`, DB head, Redis, auth, and webhook after rollback.

## Downtime Assessment

Prefer one credential class per controlled window. API-only keys may be near-zero downtime if dual credentials exist. JWT, Redis, database, webhook, and bot-token changes may require a short controlled restart or re-registration. No restart, deploy, env edit, migration, webhook change, or token rotation was performed while preparing this plan.

## Secrets Printed

NO

## Production Mutation

NONE

## Commander Decision Required

Confirm dependency order and authorize a separate execution gate with explicit credentials, owner-controlled provisioning, rollback checkpoint, and verification criteria.
