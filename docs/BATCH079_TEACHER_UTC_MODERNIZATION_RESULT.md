# BATCH079 — Teacher UTC Modernization Result

Scope: exactly two application calls in `app/api/routes/teacher.py` (publish_at and close_at). No schema, migration, DB, API contract, dependency, or unrelated datetime changes.

## Change
- `datetime.utcnow()` → `datetime.now(UTC)` at publish assignment lifecycle.
- `datetime.utcnow()` → `datetime.now(UTC)` at close assignment lifecycle.
- Added the existing compatible `UTC` import.

## Validation
- Ruff UP017 on teacher.py targeted calls: 0 findings (other pre-existing DTZ003 calls were untouched).
- py_compile teacher.py: PASS.
- Gate 078 timezone contract tests: PASS.
- Related focused tests: 7 passed, 0 failed on clean basetemp.
- Full suite: 958 passed, 0 failed, exit 0 in 764.65s.
- Warnings: 6 → 4; both application-owned teacher datetime warnings removed. Remaining 4 are dependency/tooling warnings.

## Semantics
DB columns remain `DateTime(timezone=True)` and API serialization remains ISO-8601. Existing comparison and access behavior remains covered by contract and regression tests. No migration or API shape change was made.

Production impact: NONE (local branch only).
Commit Gate 079: HOLD pending Commander approval.
