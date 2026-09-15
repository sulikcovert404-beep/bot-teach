# Ruff Phase 3 Batch 001 Selection Review — 20260915

## Candidate path discrepancy
Commander suggested `app/services/teacher.py`, but current Ruff evidence shows:
- `app/services/teacher.py`: no I001 findings (Ruff reports only an existing E902 parse/config issue).
- `app/api/routes/teacher.py`: I001=2, F401=2, B008=24, BLE001=2, DTZ003=10, F811=6, S110=2.

## Selection conclusion
The suggested services path is not a valid I001 candidate. The routes path has only two I001 findings but also behavior- and runtime-sensitive rules, so an I001-only edit must be explicitly isolated and reviewed. No source edit, import rewrite, or autofix was performed.

## Focused validation plan if routes candidate is confirmed
Run targeted I001 only, inspect import side effects, preserve all non-I001 findings, run py_compile and focused route tests, then diff-check and secret scan. Full regression is required if the import change affects runtime imports.

## Production / Recovery
Production: NONE. Recovery: SAFE HOLD.

## Commander decision required
Confirm the canonical candidate path (`app/services/teacher.py` vs `app/api/routes/teacher.py`) and whether a two-finding I001-only change on the routes module is authorized. Until confirmation: no source edit.
