# Build command: docker build -f services/control-plane/Dockerfile .
FROM python:3.12-slim

WORKDIR /app

# Copy shared libraries and install them
COPY libs/faultline-auth /libs/faultline-auth
RUN pip install --no-cache-dir /libs/faultline-auth

# Copy control-plane service and install
COPY services/control-plane /app
RUN pip install --no-cache-dir .

EXPOSE 8002

CMD ["uvicorn", "app.api_main:app", "--host", "0.0.0.0", "--port", "8002"]
