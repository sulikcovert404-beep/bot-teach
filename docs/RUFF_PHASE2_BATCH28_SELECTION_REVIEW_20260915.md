# Ruff Phase 2 Batch 28 Selection Review — 2026-09-15

Candidate: `app/services/persistence_readiness.py`

Finding: exactly 1 UP035 (`Mapping` from `typing`; `Any` remains in typing).
Blast radius: LOW; persistence readiness model, import-only remediation.
Contract/runtime risks: no behavior, readiness logic, or serialization change expected; move only Mapping.
Required validation: Ruff UP006/UP035, py_compile, focused tests, import-only diff, behavior/serialization review, git diff --check, secret scan.
Production impact: NONE.
Recovery impact: SAFE HOLD.
Recommendation: approve implementation gate limited to moving `Mapping` to `collections.abc`.
