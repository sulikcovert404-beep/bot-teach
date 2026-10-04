# Migration and backup strategy

The application uses SQLAlchemy models as the domain schema source. Production migrations must be introduced with Alembic before any deployment that persists user data.

Rules:

- every migration is forward-compatible and reviewed before production;
- CI verifies one-step downgrade followed by a full re-upgrade on a temporary database;
- destructive changes require an explicit commander decision;
- foreign keys, unique constraints, indexes and rollback impact must be reviewed;
- backups belong to the managed PostgreSQL provider and must be tested with a restore drill;
- local SQLite is only for tests and development, never production.
## Controlled migration invocation

Operational migration is a one-shot, explicitly gated service. The normal API
startup does not run migrations. Set `EXPECTED_MIGRATION_HEAD` to the exact
allow-listed target authorized by the applicable Gate, then invoke the canonical
runner through the migration-only Compose profile:

```powershell
docker compose --profile migration-gate run --rm migrate
```

The runner requires a non-empty, exact allow-listed target and rejects `head`,
unknown revisions, and missing values. Contract targets also require the exact
candidate-readiness and drain/fence/quiescence checks in order. The final 0033
target additionally requires genuine hard-crash evidence at runtime; never bake
or synthesize evidence into the image. Supply it only through the optional
read-only overlay in `compose.migration-evidence.example.yml`, using an explicitly
approved host file path. A missing or invalid evidence file fails closed.

Direct `alembic upgrade ...` commands are limited to clearly labeled local or
historical test fixtures. They are not release or production procedures.

The FastAPI lifespan disposes the cached SQLAlchemy engine on shutdown. Readiness
(`GET /health/ready`) performs a live `SELECT 1` against the configured database and
verifies that `alembic_version` matches the application migration head. A database
with pending or missing migrations is intentionally reported as not ready.

جزئیات backup، restore drill و ترتیب انتشار در [`OPERATIONS.md`](OPERATIONS.md)
ثبت شده است.
