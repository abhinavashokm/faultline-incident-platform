.PHONY: up down logs ps rebuild migrate psql test reset-db

COMPOSE = docker compose

## Start all services (uses COMPOSE_PROFILES from .env)
up:
	$(COMPOSE) up -d

## Stop and remove containers (volumes preserved)
down:
	$(COMPOSE) down

## Tail logs for all running services
logs:
	$(COMPOSE) logs -f

## Show running container status
ps:
	$(COMPOSE) ps

## Rebuild all images without cache
rebuild:
	$(COMPOSE) build --no-cache

## Run database migrations manually
migrate:
	$(COMPOSE) run --rm migrate

## Open a psql shell on the postgres container
psql:
	$(COMPOSE) exec postgres psql -U faultline

## Run pytest inside each backend service container
test:
	$(COMPOSE) exec control-plane pytest tests/
	$(COMPOSE) exec ingestion pytest tests/
	$(COMPOSE) exec processing-api pytest tests/

## ⚠️  Destroy ALL data (drops postgres volume) and restart infra
reset-db:
	@echo "⚠️  WARNING: This will DELETE all data in the Postgres volume."
	@echo "Press Ctrl+C to cancel or Enter to continue..."
	@read _confirm
	$(COMPOSE) down -v
	$(COMPOSE) up -d postgres
