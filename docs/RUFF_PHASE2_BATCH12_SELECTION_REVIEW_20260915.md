# Ruff Phase 2 Batch 12 Selection Review — 2026-09-15

Candidate: `app/services/job_lifecycle.py`

Inventory: one UP035 finding (`Mapping` imported from `typing`); current remaining inventory 895 findings. Pure job status/request/result contracts and transition validation; direct coverage exists in `tests/test_job_lifecycle.py`, with no routes, migrations, deployment scripts, or provider runtime side effects. Blast radius: LOW-MEDIUM because transition semantics are stateful contracts.

Recommendation: approve only import modernization. Preserve valid transition matrix, cancellation behavior, invalid-transition errors, and immutable result semantics. Required validation: targeted Ruff, py_compile, focused lifecycle tests, transition/cancellation behavior review, secret scan, static type validation if available. No production/recovery/migration/dependency/workflow changes. Production impact NONE; Recovery SAFE HOLD. Commander decision required before implementation.
