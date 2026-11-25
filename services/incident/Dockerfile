# Build context: repository root.
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1

RUN python -m venv /opt/venv
COPY services/incident /build/service
RUN /opt/venv/bin/pip install /build/service

FROM python:3.12-slim

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY --from=builder /opt/venv /opt/venv
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

USER appuser
EXPOSE 8004
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8004"]
