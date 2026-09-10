# app_runtime privilege matrix

Scope: disposable qualification only. No staging or production grants are included.

| Endpoint | Required tables/operations | Evidence source |
|---|---|---|
| `GET /student/profile` | `users SELECT`, `audit_logs SELECT`, `beta_quality_audits SELECT` | `app/api/routes/student.py` |
| `GET /student/v1/assignments` | `student_profiles SELECT`, `assignments SELECT`, `assignment_snapshots SELECT`, `assignment_targets SELECT`, `class_memberships SELECT` | `app/api/routes/student.py` |
| `GET /student/progress` | `beta_quality_audits SELECT`, `learning_events SELECT` | `app/api/routes/student.py` |
| `GET /teacher/profile` | `users SELECT`, `audit_logs SELECT` | `app/api/routes/teacher.py` |
| `GET /teacher/classrooms` | `audit_logs SELECT` | `app/api/routes/teacher.py` |
| `GET /teacher/dashboard/analytics` | `beta_quality_audits SELECT` | `app/api/routes/teacher.py` |
| `GET /sources/search` | `classrooms SELECT`, `teacher_profiles SELECT`, `student_profiles SELECT`, `class_memberships SELECT`, `source_chunks SELECT`, `source_documents SELECT`, `content_versions SELECT`, `teacher_content_publications SELECT` | `app/api/routes/sources.py`, `app/services/document_ingestion.py` |
| `GET /admin/users` | `users SELECT` plus admin-scoped related reads; keep separately reviewed | `app/api/routes/admin.py` |

## Grant rules

- `app_runtime`: `NOSUPERUSER`, `NOBYPASSRLS`; no `GRANT ALL`.
- Fixture creation uses `postgres`/migration owner only.
- Runtime reads use only the tables above; writes are added only where a tested endpoint requires them.
- Sequence privileges are required only for runtime inserts (`audit_logs` and explicitly tested write paths).
- Admin cross-tenant access is not implicitly granted by this matrix.

## Qualification verdict

The staging smoke showed `permission denied for table users` under `app_runtime`. The matrix identifies `users SELECT` as the first missing dependency; the disposable qualification must apply and verify the smallest complete set before any staging decision.
