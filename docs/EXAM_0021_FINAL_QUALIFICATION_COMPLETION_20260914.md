# Exam 0021 Final Qualification Completion

## Status

**PARTIAL — disposable matrix passes; HTTP/RLS visibility evidence remains incomplete.**

## Teacher PostgreSQL E2E

The disposable SQL matrix verified teacher A sees its tenant/class result and has zero cross-tenant result rows. A restricted PostgreSQL HTTP request through the full teacher route remains pending.

## School Admin PostgreSQL E2E

The disposable matrix verified tenant A data selection and no cross-school candidate. Full `app_runtime` HTTP admin route qualification remains pending.

## Time Matrix

Disposable assertions passed for open window, before `publish_at` exclusion, and after `close_at` exclusion. Existing service contract tests also pass.

## Revocation During Attempt

Policy selected for this release: active membership is required for every Exam operation. A revoked membership therefore denies save, submit, and result access even when an attempt already exists; persisted attempt/result rows remain for audit and are never deleted. Disposable route-level verification remains part of the final HTTP run.

## Legacy Negative Matrix

The direct-ID bypass endpoint was hardened and regression-tested. The remaining inventory is limited to explicitly reviewed legacy paths; no unscoped `exam_intelligence` lookup remains.

## Regression

Final targeted suite remains green: 9 contract/scope tests plus 5 Exam/resolver tests. Disposable matrix exited PostgreSQL code 0 with `ON_ERROR_STOP=1`.

## Production Mutation

NONE. Production remains pinned to `20260912_0020`; migration 0021 is not created, run, or approved for live use.

## Commander Decision Required

YES — decide the revocation policy for already-started attempts and whether dedicated restricted-role HTTP teacher/admin qualification is required before opening the production migration gate. Current verdict is **NOT READY**.
