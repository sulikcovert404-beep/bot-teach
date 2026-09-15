# Real Learning Flow E2E Audit

## Scope

Read-only audit of the current Teacher → Student → Assignment/Exam → Tutor → Progress flow. No schema, migration, provider, webhook, or production changes are included.

## Evidence

- Teacher assignment endpoints persist `Assignment`, `AssignmentTarget`, and `AssignmentSnapshot` records and expose teacher-scoped submission views.
- Student assignment endpoints require the `STUDENT` role, resolve `StudentProfile`, join class membership, and restrict results to published assignments.
- Assignment submission persists `StudentSubmission` and records an audit event; replay updates the existing submission.
- Tutor routes use the existing AI gateway and entitlement dependencies; no new provider is needed.
- Exam creation, listing, submission, and scoring endpoints exist, but the exam flow is not yet a class-assigned persisted E2E contract.

## Gaps requiring remediation

1. `GET /teacher/classrooms` returns a synthetic default classroom when no audit-created classroom exists. This must become a real empty state for the E2E flow.
2. `GET /exams/bank` returns built-in sample questions when the database is empty. This must not be used as production learning data.
3. Student progress contains fixed badge unlock timestamps, a fixed XP offset, and fixed engagement metrics (including `92.4` exam completion). These values must be derived from persisted records or represented as empty state.
4. Exam submission currently loads an exam by ID without proving the student is assigned to its classroom/tenant. Scoring also records an audit event rather than a first-class submission/result relation.
5. Exam intelligence returns fixed cohort metrics and must aggregate persisted submissions for a teacher's authorized classroom scope.
6. Teacher exam creation/assignment needs an explicit classroom target and scope check. Existing `Exam` rows are owner-based and do not establish class membership.
7. Teacher and student dashboard UI wiring must be verified against these real endpoints; placeholders and demo KPI cards must be removed from the tested flow.

## Proposed implementation order

1. Reuse existing models and audit current assignment/exam relationships; do not add a migration unless a required persisted relation is genuinely absent.
2. Remove synthetic fallback responses from the endpoints used by the E2E flow and add truthful empty states.
3. Add class-scoped exam assignment and result persistence using existing tables where possible.
4. Replace fixed progress/analytics values with aggregate queries and tenant/role scope filters.
5. Add controlled fixture tests for one teacher, one student, one class, one assignment, and one exam, including cross-tenant denial.
6. Run the existing regression suite and a Telegram Web/mobile smoke test before any production deployment decision.

## Current verdict

The flow is **partially implemented**. Assignment persistence is the strongest reusable path. Exam assignment/result persistence and truthful progress reporting are incomplete; implementation should wait for the required design/agent review and Commander approval for any schema change.
