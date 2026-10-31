# Build command from repo root: docker build -f services/processing/Dockerfile .
FROM python:3.12-slim

WORKDIR /app

# Copy shared libraries and install them
COPY libs/faultline-auth /libs/faultline-auth
RUN pip install --no-cache-dir /libs/faultline-auth

# Copy processing service and install
COPY services/processing /app
RUN pip install --no-cache-dir .

EXPOSE 8002

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]

