# Ruff Phase 2 Batch 123 Selection Review — 20260915

Candidate file: `app/services/third_development_wave_capability_selection.py`

HEAD findings: 14 (`UP006`/`UP035`), confirmed by Ruff JSON.

Remediation scope: import cleanup and `Tuple[...]` annotation modernization only. Capability-selection contract, ordering, serialization, runtime behavior, and introspection must remain unchanged.

Blast radius: isolated service decision module. Risks are limited to annotation introspection and focused test compatibility.

Validation proposed: targeted Ruff, py_compile, typing.get_type_hints, focused pytest, git diff --check, secret scan, and contract review.

Production impact: NONE
Recovery impact: SAFE HOLD

No source edit or autofix before Commander implementation approval.