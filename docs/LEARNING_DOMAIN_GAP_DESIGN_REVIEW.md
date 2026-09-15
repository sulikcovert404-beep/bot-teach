# LEARNING DOMAIN GAP DESIGN REVIEW

Status: design only. No production, database, migration, Telegram, or Cloudflare changes were made.

## Classroom

**Current:** `Classroom`, `ClassMembership`, and teacher scope resolution exist. Teacher listing falls back to a synthetic classroom when no persisted record exists.

**Target:** use `Classroom` as the only source of truth, require tenant ownership and teacher membership/assignment in every query, and return an empty list when none exists. UI must render a truthful empty state.

**Migration needed:** NO. This is endpoint and UI behavior using existing tables.

**Security:** teacher sees assigned classrooms in their tenant; student sees memberships only; school admin is tenant-scoped; super admin follows existing policy. Cross-tenant and revoked membership requests deny.

## Question Bank

**Current:** `/exams/bank` reads audit records but supplies three built-in sample questions when empty. Exam questions are persisted in `exam_questions`.

**Target:** production bank responses contain only persisted records. A dedicated persisted bank entity is preferable for filtering/ownership, but the first implementation may expose only persisted `ExamQuestion` records if the existing product contract permits. Empty database returns an explicit empty state.

**Migration needed:** NO for removing sample fallback; YES only if a standalone bank with stable subject/chapter/tenant ownership is required. No migration is proposed in this review.

**Security:** bank queries must include tenant and creator/class scope; samples belong in isolated test fixtures.

## Progress / Engagement

**Current:** assignment facts and tutor audit events exist, but progress includes fixed badge timestamps, fixed XP offset, hard-coded leaderboard, and fixed engagement KPIs.

**Target:** compute only from persisted assignment submissions, exam attempts/results, learning events, and tutor telemetry where present. Missing facts produce null/empty sections, never fabricated numbers. Leaderboards require explicit tenant/cohort scope and should be omitted until real cohort data exists.

**Migration needed:** NO for assignment/existing learning-event aggregates. YES only if exam result persistence is introduced; that is part of the Exam gate below.

**Security:** aggregate only within the authenticated student's tenant and permitted classroom set; teacher aggregates only assigned classes.

## Exam Assignment / Submission / Intelligence

**Current:** `Exam` has only owner, title, generated content, and questions. Submission accepts any `exam_id` for any authenticated user, writes an audit log, and intelligence returns fixed cohort metrics. There is no persisted class/student assignment, attempt, or result relation.

**Target canonical flow:**

```text
Exam (owner + tenant)
  -> ExamAssignment (class or student, active window)
  -> ExamAttempt (student, assignment, started/submitted)
  -> ExamAnswer / result (answers, score, graded_at)
```

Recommended ownership fields: `tenant_id` on Exam; `classroom_id` on ExamAssignment; optional `student_id` for direct assignment; immutable question snapshot/digest; unique active assignment and one or more attempts according to policy. Every read/write must join the authenticated identity to the assignment and tenant before loading or scoring.

**Migration needed:** YES. Existing schema cannot prove class/tenant authorization or persist attempts/results. Exact migration design must be a separate Gate with disposable upgrade, downgrade, and rollback rehearsal. Do not add or run it now.

**API impact:** reuse question serialization and scoring primitives; modify teacher exam create/list and student exam list/submit to require assignment scope; add assignment, attempt, result, and teacher aggregate endpoints; deprecate unauthorised `exam_id`-only submission and fixed intelligence payloads.

**Empty state:** no assigned exams returns an empty collection; no attempts returns null/empty result metrics.

## Security model

The canonical authorization boundary is the assignment join, before search or scoring:

- STUDENT: own active assignment, own attempt/result, own tenant.
- TEACHER: owned/assigned classroom and its students in own tenant.
- SCHOOL_ADMIN: own tenant.
- SUPER_ADMIN: existing audited policy.
- Cross-tenant, cross-role, revoked membership, missing assignment, and inactive assignment: DENY.

Client URL, query parameters, and submitted role values are never trusted.

## API and UI plan

Reuse existing assignment persistence and AI Tutor routes. Modify classroom, question bank, progress, and exam authorization/aggregation endpoints. Add only the exam assignment/attempt/result endpoints required by the acceptance flow. Teacher UI needs truthful class list, assignment/exam creation and result views. Student UI needs real assigned collections, attempt/submit/result views, and empty states; remove fake KPI cards.

## Test plan

1. Teacher creates/reads a persisted class and assignment.
2. Teacher assigns an exam to that class.
3. Student sees only the assigned exam, creates an attempt, submits answers, and reads persisted result.
4. Teacher reads that student's result and progress aggregates recalculate.
5. Cross-tenant, cross-role, revoked membership, inactive assignment, and unknown exam IDs all deny.
6. Empty classroom/bank/progress states return no fabricated records.
7. Existing regression and Telegram Web/mobile smoke remain green.

## External review and decision gate

External AI review is required before implementation. Handoff must contain sanitized design and relevant source excerpts only; no secrets, tokens, environment files, database dumps, logs with private data, or credentials. Claude is reserved for the tenant/data-integrity review if Sonnet 5 is available.

## Recommended implementation order

1. Remove synthetic/sample/fixed production fallbacks (no schema change).
2. Add and qualify Exam assignment/attempt/result schema in a separate migration Gate.
3. Wire scoped APIs and replace progress/intelligence with persisted aggregates.
4. Connect Teacher and Student UI and run controlled E2E fixtures.

**FINAL: READY FOR COMMANDER ARCHITECTURE DECISION**
