# Ruff Phase 2 Batch 27 Selection Review — 2026-09-15

Candidate: `app/services/pipeline_guards.py`

Finding: exactly 1 UP035 (`Mapping` from `typing`).
Blast radius: LOW; pipeline guard contract utility, import-only remediation.
Contract/runtime risks: no behavior or serialization change expected.
Required validation: Ruff UP006/UP035, py_compile, focused tests, import-only diff, behavior/serialization review, git diff --check, secret scan.
Production impact: NONE.
Recovery impact: SAFE HOLD.
Recommendation: approve implementation gate limited to moving `Mapping` to `collections.abc`.
