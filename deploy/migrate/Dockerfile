# Build context: repo root
# Used by the 'migrate' compose service to run Alembic migrations for
# control-plane and processing.

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# ── Install shared libs ───────────────────────────────────────────────────────
COPY libs/faultline-auth /build/libs/faultline-auth
RUN pip install /build/libs/faultline-auth

# ── Install control-plane (for its alembic env + models) ─────────────────────
COPY services/control-plane /app/control-plane
RUN pip install /app/control-plane

# ── Install processing (for its alembic env + models) ────────────────────────
COPY services/processing /app/processing
RUN pip install /app/processing

# ── Migration entrypoint script ───────────────────────────────────────────────
COPY deploy/migrate/migrate.sh /migrate.sh
RUN chmod +x /migrate.sh

WORKDIR /app

ENTRYPOINT ["/migrate.sh"]
