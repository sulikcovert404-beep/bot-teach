# External Telegram E2E Readiness Checklist

## Scope
Preparation only. No token rotation, webhook mutation, server change, restart, or external Telegram request was performed.

## Pre-access checklist
- [ ] Confirm owner-controlled server access and authorized deployment target.
- [ ] Confirm secret source is an environment/secret manager; never place token in chat, git, reports, Docker history, or shell history.
- [ ] Record current service/config version without exposing secrets.
- [ ] Verify health endpoint and rollback procedure before any restart.
- [ ] Verify intended webhook URL and TLS/DNS readiness; mutation requires a separate owner gate.
- [ ] Confirm isolated test Telegram account/chat and consented test messages.

## Controlled execution sequence (only after owner access)
1. Inject a fresh token through the approved secret source.
2. Controlled restart of the bot service.
3. Validate startup and `getMe` without printing token.
4. Read-only verify webhook status; change webhook only under explicit gate.
5. Send `/start` from the isolated test account.
6. Verify identity, tenant, entitlement, lesson selection, and exact approved asset.
7. Verify PDF, MCQ, descriptive, podcast, tutor response, receipt/state handling.
8. Capture request IDs/statuses and redact all sensitive content.
9. If any step fails, stop external mutation, preserve evidence, and execute rollback.

## Acceptance matrix
| Check | Evidence | Status now |
|---|---|---|
| Bot startup | service health/log status | BLOCKED_EXTERNAL |
| getMe | Telegram API response metadata | OWNER ACCESS REQUIRED |
| Webhook | read-only Telegram status | OWNER ACCESS REQUIRED |
| `/start` | isolated chat update | OWNER ACCESS REQUIRED |
| Identity/tenant/entitlement | correlated request evidence | OWNER ACCESS REQUIRED |
| Exact approved asset | asset identity/version | OWNER ACCESS REQUIRED |
| Full lesson journey | end-to-end receipt/state | OWNER ACCESS REQUIRED |

## Current verdict
Internal Telegram journey: PASS (34 focused tests; 40 internal qualification tests).
External Telegram: BLOCKED_EXTERNAL / OWNER ACTION for server access and token rotation.
Production: UNCHANGED.
