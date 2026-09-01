# Migration and backup strategy

The application uses SQLAlchemy models as the domain schema source. Production migrations must be introduced with Alembic before any deployment that persists user data.

Rules:

- every migration is forward-compatible and reviewed before production;
- destructive changes require an explicit commander decision;
- foreign keys, unique constraints, indexes and rollback impact must be reviewed;
- backups belong to the managed PostgreSQL provider and must be tested with a restore drill;
- local SQLite is only for tests and development, never production.

