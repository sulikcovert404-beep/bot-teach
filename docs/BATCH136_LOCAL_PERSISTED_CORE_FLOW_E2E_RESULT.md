# Gate 136 — Local Persisted Core Flow E2E Qualification

Date: 2026-09-17
Environment: local disposable SQLite only
Production/server: untouched

## Scope

The existing persistence harness was reused. No Docker, package installation, migration, schema creation, server, Telegram, provider, environment, or Secure Role Preview changes were made.

## Results

| Qualification | Result | Evidence |
|---|---|---|
| Persistence across engine/session restart | PASS | `tests/test_persisted_retrieval_qualification.py` |
| Assignment contract: tenant/membership/entitlement/time boundaries | PASS | `tests/test_assignment_contract.py` |
| Assignment persistence models | PASS | `tests/test_assignment_persistence_models.py` |
| Focused persisted tests | PASS | 7 passed, 0 failed, exit 0 |
| API route/auth E2E collection | BLOCKED | FastAPI import requires missing `python-multipart` |
| Full suite | NOT RUN | Collection blocker; no dependency installed per gate |

## Persisted flow evidence

The disposable harness created and committed tenant, school-admin membership, teacher and student profiles, classroom and class membership, disposed the engine, created a fresh engine, and verified all persisted records and relationships. This proves storage across separate engine/session boundaries for the covered entities.

## Negative/security coverage

The existing assignment contract tests prove tenant, enrollment, entitlement, publication and close-time decisions. The requested full application negative matrix (unassigned student, wrong class/tenant, other student's result, teacher ownership, duplicate submit, and legacy `exam_id` bypass) could not be qualified end-to-end because importing `app.main` fails before collection when `python-multipart` is unavailable. No PASS is claimed for those routes.

## Blocking defect

`app.main` imports `app.api.routes.admin_content`, whose file-upload route requires `python-multipart`. The dependency is absent from the local environment. Installing it was prohibited by Gate 136, so route-level persisted E2E remains unverified.

## Validation

- Focused tests: 7 passed / 0 failed
- No code or configuration changes
- No production impact
- Gate 136 commit: HOLD

## Verdict

`PARTIAL — PERSISTENCE CORE QUALIFIED; APPLICATION E2E BLOCKED BY MISSING TEST DEPENDENCY`
