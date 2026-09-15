# Exam 0021 Final Qualification

## Status

**PARTIAL — student persistence path PASS; final gate remains open.**

## Teacher Scope

Existing teacher tenant/class isolation and result-scope tests pass in the repository suite. No new privilege is granted by this gate. PostgreSQL teacher-result visibility under the restricted runtime was not part of the disposable Student E2E harness.

## Admin Scope

Existing school-admin tenant-scope tests pass. Cross-tenant denial is covered at policy level; PostgreSQL end-to-end admin visibility remains a separate qualification item.

## Security Matrix

- Student missing/revoked membership: DENY PASS in restricted PostgreSQL E2E.
- Cross-tenant and wrong-student attempt lookups: tenant + student predicates enforced by patched routes; direct PostgreSQL E2E negative matrix remains to be expanded.
- Legacy direct `exam_id` paths: audit pending; no production bypass is authorized.

## Time Boundaries

The Exam service enforces publish, due, and close windows. Existing assignment contract tests pass; a complete PostgreSQL E2E time-boundary matrix remains pending.

## Revocation

Resolver revocation (inactive/revoked membership) denies before Exam access. Membership removal/revocation during an active persisted attempt requires a dedicated final negative test.

## Regression

Targeted regression: `pytest -q tests/test_tenant_concurrency_qualification.py tests/test_admin_scope.py tests/test_exam_generation_route.py tests/test_exam_correction_route.py` → **7 passed, 0 failed**.

## Production Mutation

NONE. Production remains pinned to `20260912_0020`; migration 0021 is not created, run, or approved for live environments.

## Commander Decision Required

YES — final qualification still requires PostgreSQL disposable teacher/admin visibility, complete time/revocation/legacy negative matrix, and any required full regression after service changes. Do not promote migration 0021 yet.
