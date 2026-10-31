# Build context: repo root
# docker build -f services/control-plane/Dockerfile .

# ── Builder stage ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Install shared lib: faultline-auth
COPY libs/faultline-auth /build/libs/faultline-auth
RUN pip install --prefix=/install /build/libs/faultline-auth

# Install control-plane service (copy pyproject first for layer caching)
COPY services/control-plane/pyproject.toml /build/service/pyproject.toml
COPY services/control-plane /build/service
RUN pip install --prefix=/install /build/service

# ── Final stage ───────────────────────────────────────────────────────────────
FROM python:3.12-slim AS final

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Create non-root user
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

WORKDIR /app

# Copy service source (will be overridden by bind-mount in dev)
COPY services/control-plane /app

# Keys are volume-mounted at runtime; do not bake into image
# ./services/control-plane/keys:/app/keys:ro

RUN chown -R appuser:appgroup /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.api_main:app", "--host", "0.0.0.0", "--port", "8000"]
