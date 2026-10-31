# Build context: repo root
# docker build -f services/processing/Dockerfile .

# ── Builder stage ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Use a venv so pip can see the shared libs when resolving the service's dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /build

# Install shared lib: faultline-auth
COPY libs/faultline-auth /build/libs/faultline-auth
RUN pip install /build/libs/faultline-auth

# Install processing service
COPY services/processing /build/service
RUN pip install /build/service

# ── Final stage ───────────────────────────────────────────────────────────────
FROM python:3.12-slim AS final

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PATH="/opt/venv/bin:$PATH"

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the virtualenv from builder
COPY --from=builder /opt/venv /opt/venv

# Create non-root user
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

WORKDIR /app

# Copy service source (will be overridden by bind-mount in dev)
COPY services/processing /app

# Keys are volume-mounted at runtime; do not bake into image
# ./services/processing/keys:/app/keys:ro

RUN chown -R appuser:appgroup /app
USER appuser

EXPOSE 8002

# Default: HTTP API. Override in compose for worker role.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]