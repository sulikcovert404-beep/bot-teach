# Exam 0021 Application-Level PostgreSQL Qualification

Status: PARTIAL  
Mode: Disposable / isolated only  
Production mutation: NONE

## PostgreSQL runtime role

On a disposable PostgreSQL 16/pgvector instance, role `app_runtime_qual` was created with `NOSUPERUSER` and `NOBYPASSRLS`. It received only disposable database grants. No production role was changed.

## RLS enforcement

With tenant context set transaction-locally:

- tenant A saw only its exam row (`1`).
- tenant B saw only its exam row (`1`).
- missing context saw zero rows.
- a tenant-B insert while tenant-A context was active was rejected by the RLS policy.

RLS/forced-RLS and tenant policies were already verified during the migration qualification. The disposable database and role were removed after testing.

## Application E2E and remaining gaps

The following application-level scenarios were not claimed as PASS in this run and require a dedicated fixture-driven PostgreSQL test harness:

- student start/snapshot/save/submit/result flow;
- teacher class-result visibility and school-admin scope;
- concurrent start and atomic attempt numbering;
- unassigned, wrong-class, cross-tenant and other-student denial;
- membership removal/revocation denial;
- publish/close boundaries and legacy `exam_id` bypass;
- identity mapping from Telegram user to student/tenant membership.

Static review also found that `app/services/exam_attempts.py` performs tenant predicates but does not itself set `app.tenant_id`. Under forced RLS, the application request boundary must inject transaction-local context before these calls; this integration point is not qualified by the current unit tests.

## Verdict

Restricted-role RLS behavior: **PASS**.  
Application-level Exam E2E/security suite: **NOT YET QUALIFIED**.  
Production migration `20260912_0021`: **NO-GO**.  
Production remains pinned to `20260912_0020`.

## Commander Decision Required

Approve implementation or execution of the fixture-driven application PostgreSQL qualification harness, still on disposable infrastructure only.
