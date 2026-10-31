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
cp deploy/migrate/.env.example          deploy/migrate/.env
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
cp .env.example .env
# … edit .env, create keys (see above) …

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
| Control Plane API | http://localhost:8000 |
| Ingestion API | http://localhost:8001 |
| Processing API | http://localhost:8002 |
| Frontend (Next.js) | http://localhost:3000 |
| Mailpit UI (email) | http://localhost:8025 |
| Postgres | localhost:5432 |
| Kafka | localhost:9092 |
| Redis | localhost:6379 |

---

## Compose Profiles

Services are grouped by profile so you can start only what you need:

| Profile | Services started |
|---|---|
| *(none)* | postgres, kafka, mailpit, redis (infra always) |
| `backend` | + migrate, control-plane, ingestion, processing-api, processing-worker |
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

```
postgres (healthy)
    └─► migrate (runs alembic for control-plane + processing, then exits)
            ├─► control-plane (healthy) ──► ingestion
            └─► processing-api
            └─► processing-worker
kafka (healthy) ──► ingestion, processing-api, processing-worker
redis (healthy) ──► ingestion
control-plane (healthy) ──► frontend
```

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
make test        # Run pytest in each backend container
make reset-db    # ⚠️ Destroy postgres volume and restart
```

---

## Hot Reload (Development)

All backend services bind-mount their `app/` directory into the container and run uvicorn with `--reload`. Editing Python source on the host triggers an automatic reload inside the container.

The frontend runs `npm run dev` (Next.js dev server) with `WATCHPACK_POLLING=true` so HMR works correctly on Linux hosts. The `frontend_node_modules` named volume prevents the host bind-mount from overwriting the container's `node_modules`.

---

## Running Migrations Manually

Migrations are run automatically by the `migrate` container at startup. To run them again manually:

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

Shared libraries installed per service:

| Service | Shared lib |
|---|---|
| control-plane | `faultline-auth` |
| ingestion | `faultline-events` |
| processing-api / processing-worker | `faultline-auth` |
| migrate | `faultline-auth` (control-plane dep) |

---

## Known Gaps

- **No CORSMiddleware** is present in any backend service. If the frontend needs to call the APIs directly from the browser (not via a proxy), CORS headers must be added to control-plane, ingestion, and processing-api.
- **alerting, incident, investigation** services are not yet implemented and have no compose entries.
- **Dead-letter queue** for Kafka consumer permanent failures is planned but not yet implemented.
