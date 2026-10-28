# Faultline: rules for AI coding agents

Monorepo for an error tracking and incident response platform with 6 services:
control-plane, ingestion, processing, alerting, incident, investigation.
Read docs/project-context.md and docs/schema.dbml before designing anything.
The schema is the source of truth. Never change it without asking.

## Architecture
- Python 3.12, FastAPI, SQLAlchemy 2.0 async with asyncpg, Alembic, aiokafka.
- Layers: router/consumer -> service -> repository -> models. Dependencies point one way.
- Routers and consumers are thin. Services own business rules and transactions.
  Repositories contain queries only and never commit.
- Each service owns its own database schema and its own Alembic migrations.
  Never create tables from app code (no create_all). Never read another service's DB.
- No service imports another service's code. Only Kafka event schemas are shared (libs/events).
- Config comes from environment variables via pydantic-settings. No hardcoded hosts.

## Kafka and reliability
- At-least-once delivery. Commit the offset only after the DB transaction commits.
- Writes must be idempotent (primary key on event id, ON CONFLICT DO NOTHING).
- Bad messages raise PermanentError (log and skip, DLQ later). Transient errors
  propagate without committing so the message is redelivered.

## Conventions
- Type hints everywhere, small functions, use logging (never print).
- Do not add dependencies, features or files outside the task. Do not touch other services.
- Never run docker, alembic or database commands. Tell me which commands to run.
- Finish with a list of the files you created or changed.