# EXAM PERSISTENCE AI TEAM REVIEW

## Scope
Design review only. No migration, schema, production, Telegram, or Cloudflare changes were made.

## Gemini response
Gemini supports separating the exam definition from assignment and execution records. It recommends immutable question snapshots or version identifiers, explicit tenant ownership, authorization before load/scoring, server-side timing, attempt constraints, idempotent answer upserts, and persisted progress. It flags duplication with the existing Assignment domain, IDOR risk without composite tenant constraints, membership revocation during active attempts, and legacy backfill/rollback concerns. Persian handling should normalize glyphs and digits while keeping semantic text separate from presentation directionality.

## Codex validation
The current `Exam` model is owner-based (`user_id`) and lacks tenant/classroom scope, attempts, answers, or persisted results. The existing Assignment models already provide tenant, classroom, target, snapshot, submission, and review concepts. The exam submit route loads by exam id, scores in memory, and writes an audit record without a persisted attempt/result or assignment authorization. Therefore the schema gap and the authorization risk are real; a separate migration and endpoint integration gate is required.

## Common points
- Reuse existing Assignment targeting/snapshot concepts where possible.
- Freeze the question set for each published execution.
- Authorize tenant, classroom/enrollment, assignment window, and attempt budget before loading/scoring.
- Persist attempts, answers, results, and grading lineage; derive progress from those facts.
- Use atomic/idempotent operations for starts, answer saves, and submission.
- Preserve legacy personal exams through additive, backward-compatible migration and feature-flagged rollout.
- Fail closed on revoked membership and cross-tenant identifiers.
- Normalize Persian characters/digits deterministically; keep RTL presentation in the UI.

## Conflicts / decisions needed
- Whether `ExamAssignment` should be a new entity or an exam-specific projection/link over existing `Assignment`; duplication would create divergent targeting and notification behavior.
- Whether to enforce composite `(id, tenant_id)` foreign keys immediately or phase them in after application authorization is proven.
- Whether legacy `tenant_id IS NULL` exams remain personal drafts or are assigned to a dedicated legacy tenant.
- Exact expiry policy: reject after server-time deadline, allow bounded grace, or auto-submit expired attempts.

## Recommended minimal design
1. Keep `Exam` as an immutable/versioned definition with owner/tenant metadata.
2. Reuse `Assignment` for classroom/student targeting and publication windows; add only an explicit exam reference if compatible with current models. Introduce a separate `ExamAssignment` only if reuse cannot represent exam semantics.
3. Add persisted `ExamAttempt`, `ExamAnswer`, and `ExamResult` with tenant linkage, explicit state machine, unique attempt numbering, grading lineage, and frozen question/version reference.
4. Enforce authorization before object load/scoring and use database-time checks plus atomic constraints.
5. Make new tables additive; backfill only validated legacy records; preserve rollback by leaving legacy read paths intact.
6. Add negative, concurrency, deadline, revocation, Persian normalization, and cross-tenant tests before any live migration.

## Commander decision required
Approve the exact entity boundary and migration strategy. After approval, create a separate migration qualification gate on disposable DB, then implement endpoint/UI integration. Until that decision, implementation remains intentionally blocked.
