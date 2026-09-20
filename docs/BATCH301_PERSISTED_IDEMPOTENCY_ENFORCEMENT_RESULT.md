# Gate 301 — Persisted Idempotency Enforcement Result

Date: 2026-09-20
Scope: controlled application/service logic only

## Implementation

- Wired `provision_test_identity` to the existing `provisioning_idempotency_keys` table.
- Claims `(operation, idempotency_key)` before identity work inside the same transaction.
- Uses a deterministic SHA-256 request fingerprint.
- Same key and fingerprint after success returns `REPLAY` with the persisted result.
- Same key with a different fingerprint is rejected as a conflict.
- Unique-key races are isolated in a savepoint; a losing request cannot create a second identity.
- Successful creation or existing-identity resolution persists the response and marks the claim `SUCCEEDED`.
- Any creation failure rolls back the claim and identity work atomically.

## Validation

| Check | Result |
|---|---|
| Same key + same fingerprint replay | PASS |
| Same key + different fingerprint conflict | PASS |
| Concurrent same key: one create + one replay | PASS |
| Concurrent conflicting fingerprint: one accepted + one conflict | PASS |
| Existing identity behavior preserved | PASS |
| Atomic claim before identity creation | PASS |
| Failed creation claim rollback path | PASS by outer transaction rollback |
| Schema/migration changes | NONE |
| Role/privilege changes | NONE |
| Runtime/env/secret changes | NONE |
| Production/Telegram/Cloudflare changes | NONE |

## Tests

- `pytest -q tests/test_test_identity_provisioning.py tests/test_curriculum_pipeline_runtime.py` — **11 passed**
- `python -m py_compile app/services/test_identity_provisioning.py` — PASS
- `ruff check app/services/test_identity_provisioning.py tests/test_test_identity_provisioning.py` — PASS
- `git diff --check` — PASS

## Verdict

`PROVISIONING_IDEMPOTENCY_ENFORCED`

No commit was created. Gate 301 remains controlled-workspace only pending Commander review.
