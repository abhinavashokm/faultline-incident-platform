# Docker & Local Development

This document describes how to run the full Faultline platform locally using Docker Compose.

## Prerequisites

- Docker ≥ 24 with Compose v2 (the `docker compose` plugin, not `docker-compose`)
- `make` (optional but recommended)
- RSA key pairs for the JWT-signing services (see [Key Setup](#key-setup))

---

## Key Setup

Control-plane and processing each need RSA PEM files on disk. These are **git-ignored** and must be created once:

```bash
# Control-plane signing key pair
mkdir -p services/control-plane/keys
openssl genrsa -out services/control-plane/keys/private.pem 2048
openssl rsa -in services/control-plane/keys/private.pem \
            -pubout -out services/control-plane/keys/public.pem

# Processing public key (copy from control-plane)
mkdir -p services/processing/keys
cp services/control-plane/keys/public.pem services/processing/keys/public.pem
```

---

## Environment Files

Copy the root example and each service example, then edit secrets:

```bash
cp .env.example .env
cp services/control-plane/.env.example  services/control-plane/.env
cp services/ingestion/.env.example      services/ingestion/.env
cp services/processing/.env.example     services/processing/.env
cp services/gateway/.env.example        services/gateway/.env
cp services/alerting/.env.example       services/alerting/.env
```

> **Important:** In the service `.env` files the `localhost` references are only used for local (non-Docker) development. When running via compose, the `environment:` block in `docker-compose.yml` overrides those values with the correct container hostnames automatically.

Secrets that **must** be changed before first run:

| Variable | Where | Notes |
|---|---|---|
| `CONTROL_PLANE_INTERNAL_SERVICE_SECRET` | `services/control-plane/.env` | `openssl rand -hex 32` |
| `CONTROL_PLANE_SERVICE_TOKEN` | `services/ingestion/.env` | Same value as above |
| `CONTROL_PLANE_OTP_HMAC_SECRET` | `services/control-plane/.env` | `openssl rand -hex 32` |

---

## Quick Start

```bash
# 1. First-time setup
# Create the environment files and keys using the steps above.

# 2. Start everything
make up
# or: docker compose up -d

# 3. Check status
make ps

# 4. Tail logs
make logs
```

Services and their ports once healthy:

| Service | URL |
|---|---|
| Gateway | http://localhost:8000 |
| Control Plane API | http://localhost:8010 |
| Ingestion API | http://localhost:8001 |
| Processing API | http://localhost:8002 |
| Alerting API | http://localhost:8003 |
| Frontend (Next.js) | http://localhost:3000 |
| Mailpit UI (email) | http://localhost:8025 |
| Postgres | localhost:5432 |
| Kafka | localhost:9092 |
| Redis | localhost:6379 |

---

The interactive API references are available for [Control Plane](http://localhost:8010/docs), [Ingestion](http://localhost:8001/docs), [Processing](http://localhost:8002/docs), and [Alerting](http://localhost:8003/docs).

## Compose Profiles

Services are grouped by profile so you can start only what you need:

| Profile | Services started |
|---|---|
| *(none)* | postgres, kafka, mailpit, redis (infra always) |
| `backend` | + migrate, gateway, control-plane, ingestion, Processing API and workers, Alerting API and workers, Incident API |
| `frontend` | + frontend |

The root `.env` sets `COMPOSE_PROFILES=backend,frontend` by default, so `docker compose up -d` starts everything.

```bash
# Infra only
COMPOSE_PROFILES= docker compose up -d

# Backend only (no frontend)
COMPOSE_PROFILES=backend docker compose up -d

# All
COMPOSE_PROFILES=backend,frontend docker compose up -d
```

---

## Startup Order

Compose waits for PostgreSQL before running the migration job for Control Plane, Processing, Alerting, and Incident. Kafka initialization creates the topics used by the workers. The gateway waits for its upstream services to become healthy. Use `make ps` and `make logs` to diagnose startup failures.

---

## Common Commands

```bash
make up          # Start all services
make down        # Stop containers (volumes kept)
make logs        # Tail all logs
make ps          # Show container status
make rebuild     # Rebuild all images without cache
make migrate     # Run migrations manually
make psql        # Open psql shell on postgres
make test        # Run pytest in control-plane, ingestion, and processing-api
make reset-db    # ⚠️ Destroy postgres volume and restart
```

---

## Hot Reload (Development)

Backend API containers bind-mount their `app/` directories and run Uvicorn with `--reload`. Restart worker containers after editing worker code.

The frontend runs `npm run dev` (Next.js dev server) with `WATCHPACK_POLLING=true` so HMR works correctly on Linux hosts. The `frontend_node_modules` named volume prevents the host bind-mount from overwriting the container's `node_modules`.

---

## Running Migrations Manually

Migrations for Control Plane, Processing, Alerting, and Incident run automatically in the `migrate` container at startup. To run them again manually:

```bash
make migrate
# or
docker compose run --rm migrate
```

Commands to generate and apply new migrations (run from the relevant service directory):

```bash
# control-plane
cd services/control-plane
alembic revision --autogenerate -m "describe change"
alembic upgrade head

# processing
cd services/processing
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

---

## Image Architecture

All Python service images use a **multi-stage build** (`builder` → `final`) from the **repo root** as build context:

1. **builder** – installs shared libs and the service into `/install` using `pip install --prefix`
2. **final** – copies `/install` into a clean `python:3.12-slim` image; runs as a non-root `appuser`

For service ownership and shared contracts, see [Architecture](architecture.md).

---

## Verifying Notification Channel Confirmation Emails with Mailpit

Faultline uses [Mailpit](https://github.com/axllent/mailpit) as a local SMTP sink.

When an email notification channel is created:
1. Ensure Mailpit is running (`docker compose up -d mailpit`).
2. Create an email notification channel:
   ```bash
   curl -X POST http://localhost:8000/api/v1/projects/<project_id>/notification-channels \
     -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Dev On-Call",
       "channel_type": "email",
       "destination": "devs@faultline.io",
       "enabled": true
     }'
   ```
3. Open http://localhost:8025 in your browser to view the confirmation email captured by Mailpit.

---

## Known Gaps

- **Incident and investigation** are planned and have no Compose entries.
- **Dead-letter queue** for Kafka consumer permanent failures is planned but not yet implemented.
