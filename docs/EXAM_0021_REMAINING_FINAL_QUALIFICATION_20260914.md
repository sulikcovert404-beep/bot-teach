# Exam 0021 Remaining Final Qualification

## Status

**PARTIAL — migration remains NO-GO.**

## Teacher PostgreSQL E2E

Student persistence E2E and tenant context passed on restricted PostgreSQL. Existing teacher result visibility query is tenant-linked through `Assignment → Classroom → TeacherProfile` and repository scope tests pass, but a dedicated restricted-role PostgreSQL teacher-result request was not executed in this run.

## School Admin PostgreSQL E2E

Existing school-admin tenant scope tests pass. A dedicated PostgreSQL HTTP visibility run remains pending.

## Time Matrix

Service contract tests pass for before `publish_at`, before `due_at`, and after `close_at` denial/allowance. Full persisted PostgreSQL matrix remains pending.

## Revocation During Attempt

Resolver denies revoked membership before a new Exam operation. Product policy for an already-started attempt after revocation is not yet explicitly qualified; no assumption is made about submit/result behavior.

## Legacy Audit

**HIGH finding:** `app/api/routes/exams.py` endpoint `exam_intelligence` calls `session.get(Exam, exam_id)` without tenant scope or membership authorization. This is a potential cross-tenant/legacy direct-ID bypass and must be fixed or explicitly excluded before migration approval. Other owner-scoped paths use `user_id` but still require a separate tenant policy review.

## Regression

`pytest -q tests/test_assignment_contract.py tests/test_tenant_concurrency_qualification.py tests/test_admin_scope.py` → **9 passed, 0 failed**.

## Production Mutation

NONE. No Alembic revision or live schema/role/config/deploy change. Production remains `20260912_0020`.

## Commander Decision Required

YES — authorize a focused legacy endpoint hardening gate and dedicated PostgreSQL teacher/admin/time/revocation qualification. Until the `exam_intelligence` finding and remaining E2E evidence are closed, Exam 0021 migration is not ready.
