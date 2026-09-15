# Ruff Phase 2 Batch 13 Selection Review — 2026-09-15

Candidate: `app/services/lesson_pack.py`

Inventory: one UP035 (`Mapping` from `typing`); remaining inventory 894 findings. The module defines lesson-pack request/service contracts with direct coverage in `tests/test_lesson_pack.py` and orchestrator integration tests. It has no migration, deployment, or provider side effects. Blast radius: MEDIUM because lesson generation and reuse contracts are product-facing.

Recommendation: approve only import modernization in this file. Preserve pack validation, stage selection, deterministic reuse/version behavior, and Persian text handling. Required validation: targeted Ruff, py_compile, focused lesson-pack and orchestrator tests, behavior/digest diff review, secret scan, static type validation if available. No production/recovery/migration/dependency/workflow changes. Production impact NONE; Recovery SAFE HOLD. Commander decision required before implementation.
