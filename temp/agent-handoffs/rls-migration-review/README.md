# RLS migration review handoff

Sanitized source only. No credentials, environment values, private data, or production configuration.

Base revision: 20260909_0015
Draft revision: 20260910_0016
Selected tables are listed in the migration file. Policy uses transaction-local canonical `app.tenant_id`; unset context must fail closed. Review SQL semantics, nullable tenant handling, ownership boundaries, pooling, admin/jobs, and rollback. Advisory only; do not implement or execute.
