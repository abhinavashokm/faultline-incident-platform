# Build command from repo root: docker build -f services/ingestion/Dockerfile .
FROM python:3.12-slim

WORKDIR /app

# Copy shared libraries and install them
COPY libs/events /libs/events
RUN pip install --no-cache-dir /libs/events

# Copy ingestion service and install
COPY services/ingestion /app
RUN pip install --no-cache-dir .

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]

