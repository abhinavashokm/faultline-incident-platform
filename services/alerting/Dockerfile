# Build context: repo root
# docker build -f services/alerting/Dockerfile .

# ── Builder stage ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /build

# Install shared lib: faultline-auth
COPY libs/faultline-auth /build/libs/faultline-auth
RUN pip install /build/libs/faultline-auth

# Install alerting service
COPY services/alerting /build/service
RUN pip install /build/service

# ── Final stage ───────────────────────────────────────────────────────────────
FROM python:3.12-slim AS final

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PATH="/opt/venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv

RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

WORKDIR /app

COPY services/alerting /app

RUN chown -R appuser:appgroup /app
USER appuser

EXPOSE 8003

# Default: HTTP API. Override in compose for worker roles.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
