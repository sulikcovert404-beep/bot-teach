# Migration and backup strategy

The application uses SQLAlchemy models as the domain schema source. Production migrations must be introduced with Alembic before any deployment that persists user data.

Rules:

- every migration is forward-compatible and reviewed before production;
- CI verifies one-step downgrade followed by a full re-upgrade on a temporary database;
- destructive changes require an explicit commander decision;
- foreign keys, unique constraints, indexes and rollback impact must be reviewed;
- backups belong to the managed PostgreSQL provider and must be tested with a restore drill;
- local SQLite is only for tests and development, never production.
## Production database

Production uses PostgreSQL through `DATABASE_URL` with the `asyncpg` driver. The
Docker Compose stack provisions PostgreSQL with a persistent named volume and
waits for its health check before starting the API. Run migrations explicitly
before serving traffic:

```powershell
docker compose run --rm api alembic upgrade head
```

The FastAPI lifespan disposes the cached SQLAlchemy engine on shutdown. Readiness
(`GET /health/ready`) performs a live `SELECT 1` against the configured database and
verifies that `alembic_version` matches the application migration head. A database
with pending or missing migrations is intentionally reported as not ready.

جزئیات backup، restore drill و ترتیب انتشار در [`OPERATIONS.md`](OPERATIONS.md)
ثبت شده است.
