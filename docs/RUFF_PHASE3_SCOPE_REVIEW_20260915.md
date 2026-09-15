# Ruff Phase 3 Scope Review — 20260915

## Status
Selection and planning only. No source edits, autofix, configuration, dependency, workflow, production, or recovery actions were performed.

## Current findings
A full `ruff check app --output-format=json` on the current worktree reports **880 findings** across the application.

Top rule families:
- F401: 342 (unused imports)
- B008: 248 (function-call-in-default-argument patterns; behavior-sensitive)
- I001: 161 (import ordering)
- UP017: 24 (annotation modernization)
- BLE001: 14 (broad exception handling)
- DTZ003: 13 (timezone-sensitive behavior)
- UP045: 10
- F811: 10 (redefinition; behavior/import-sensitive)
- F841: 7
- UP037: 6
- PIE794: 6

## Risk categorization
- Import-only candidates: I001 and a subset of F401, subject to side-effect review.
- Annotation-only candidates: UP017, UP045, UP037; require Python 3.12 and introspection checks.
- Behavior-sensitive: B008, BLE001, DTZ003, F811, F841, and remaining correctness/style rules.
- Runtime-sensitive: route-heavy modules with B008 and exception/time handling findings.

## Blast radius
Largest concentration is in `app/api/routes/teacher.py` (48), `pilot_preparation.py` (30), `student.py` (25), `admin.py` (19), and `exams.py` (18). These are API/security-sensitive and should not be batch-autofixed.

## Recommendation
Continue the successful batch pattern only for explicitly selected import-only or annotation-only files. Create a separate gate for behavior-sensitive rules, starting with a selection review and focused tests. Do not use broad `ruff --fix`.

## Validation plan for any future batch
Ruff targeted rule check, py_compile, type/introspection checks, focused tests, diff review, secret scan, and explicit contract/runtime review. Full regression is required when runtime or API code changes.

## Production / Recovery
Production: NONE. Recovery: SAFE HOLD.

## Commander decision required
Select the next rule family and candidate file, and issue an implementation gate. Until then: no source edit, no autofix, no refactor, no deployment or recovery action.
