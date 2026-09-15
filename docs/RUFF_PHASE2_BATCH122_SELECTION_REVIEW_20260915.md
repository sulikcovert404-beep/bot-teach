# Ruff Phase 2 Batch 122 Selection Review — 20260915

Candidate file: `app/services/rag_regression_validation_suite.py`

HEAD findings: 14 (`UP006`/`UP035`), confirmed by Ruff JSON.

Remediation scope: import cleanup and `Tuple[...]` annotation modernization only. RAG regression validation behavior, contracts, serialization, and runtime semantics must remain unchanged.

Blast radius: isolated validation service. Risks are limited to annotation introspection and test discovery.

Validation proposed: targeted Ruff, py_compile, typing.get_type_hints, focused pytest, git diff --check, secret scan, and contract review.

Production impact: NONE
Recovery impact: SAFE HOLD

No source edit or autofix before Commander implementation approval.