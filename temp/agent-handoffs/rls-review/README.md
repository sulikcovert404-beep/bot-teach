# RLS selected-table evidence handoff

Sanitized repository evidence for adversarial policy review. No secrets or credentials.

Candidate tables discovered by information_schema on staging: assignment_snapshots, assignment_statuses, assignment_targets, assignments, classrooms, content_generation_jobs, student_submissions, submission_reviews, teacher_profiles.

All candidate tables currently contain zero rows in staging; no data mutation performed.

Policy design must use canonical tenant context via transaction-local `set_config('app.tenant_id', ..., true)` and fail closed when unset. Do not use Telegram IDs or channel identifiers.
