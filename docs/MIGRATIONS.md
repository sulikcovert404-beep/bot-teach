# Migration and backup strategy

The application uses SQLAlchemy models as the domain schema source. Production migrations must be introduced with Alembic before any deployment that persists user data.

Rules:

- every migration is forward-compatible and reviewed before production;
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
(`GET /health/ready`) performs a live `SELECT 1` against the configured database.
