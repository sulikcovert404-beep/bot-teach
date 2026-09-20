# Gate 303 — Provisioning Audit & Observability Result

Date: 2026-09-20
Scope: read-only qualification and isolated test evidence

## Audit checks

| Check | Result | Evidence |
|---|---|---|
| Provisioning success audit row | PASS | `TEST_IDENTITY_PROVISIONED` / `TEST_IDENTITY_PROVISIONING_EXISTING` are emitted |
| Result is persisted without secret material | PASS | audit repository rejects keys containing password/secret/token/api_key/authorization; focused tests pass |
| Idempotency replay/conflict visibility | PASS | persisted status/fingerprint/operation are distinguishable; service returns `REPLAY` or conflict |
| Failed transaction traceability | PASS | transaction rollback leaves no half-created identity or durable CLAIMED row |
| Token/password/initData logging | PASS | no such fields are accepted by audit metadata path |
| Correlation identifier propagation | ISSUE | `ProvisioningIdempotencyKey.correlation_id` remains NULL because the service/endpoint contract provides no correlation id |
| Timestamps / operation / fingerprint | PASS | persisted idempotency record fields exist and are populated by the application path |

## Validation

- `pytest -q tests/test_test_identity_provisioning.py tests/test_curriculum_pipeline_runtime.py` — 11 passed
- `ruff check app/services/test_identity_provisioning.py tests/test_test_identity_provisioning.py` — PASS
- `python -m py_compile app/services/test_identity_provisioning.py` — PASS
- No staging/production read or write was performed.

## Finding

Audit redaction and replay/conflict visibility are qualified. A correlation id cannot be qualified as propagated because the current provisioning API/service signature has no correlation-id input and writes NULL to the existing nullable column. This is an observability contract gap, not a schema or security failure.

## Verdict

`PROVISIONING_AUDIT_ISSUE_FOUND`

Recommended follow-up: a separate controlled application contract gate to thread an externally supplied correlation id through the endpoint, service, audit metadata, and idempotency row. No implementation was made in Gate 303.
