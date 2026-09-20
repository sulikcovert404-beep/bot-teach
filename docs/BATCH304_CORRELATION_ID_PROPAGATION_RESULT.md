# Gate 304 — Correlation ID Propagation Result

Date: 2026-09-20
Scope: controlled application logic; no schema or environment changes

## Implementation

- The admin provisioning endpoint now accepts the standard `X-Correlation-ID` request header.
- The service propagates that value into `ProvisioningIdempotencyKey.correlation_id`.
- When the header is absent, a server-generated UUID is used.
- The generated/supplied correlation id is carried into provisioning audit metadata.
- Idempotency fingerprints remain unchanged and correlation ids are not user-controlled secrets.
- Replay returns the persisted original result and retains the original correlation id.

## Validation

| Scenario | Result |
|---|---|
| Supplied correlation id persisted | PASS |
| Missing correlation id generates UUID | PASS |
| Replay retains original correlation id | PASS |
| Conflict remains traceable by correlation record | PASS |
| Sensitive token/password/secret fields logged | NONE |
| Focused tests | 11 passed |
| py_compile (service + route) | PASS |
| Ruff (changed service/tests) | PASS |
| Schema/migration/role/privilege changes | NONE |
| Env/secret/production/Telegram/Cloudflare changes | NONE |

## Verdict

`CORRELATION_PROPAGATION_QUALIFIED`

No commit was created. The change remains controlled-workspace only pending Commander review.
