# Ruff Phase 2 Batch 106 Selection Review — 2026-09-15

Candidate: `app/services/rag_confidence_conflict_decision_wave.py`
HEAD findings: 17 UP006/UP035 (Ruff JSON).
Symbols: deprecated typing collection imports and annotations; audit exact symbols before implementation.
Remediation: import cleanup plus annotation modernization; selection only, no source edit authorized yet.
Blast radius: localized RAG confidence conflict decision contract.
Risks: verify field shape, defaults, ordering, serialization, runtime and introspection compatibility.
Focused tests: discover before implementation.
Validation proposed: targeted Ruff, py_compile, typing.get_type_hints, focused pytest, scope/diff check, secret scan.
Production impact: NONE
Recovery impact: SAFE HOLD

Status: Selection review only; no source change, autofix, refactor, dependency/config/workflow change, migration, deployment, or production/recovery action.
