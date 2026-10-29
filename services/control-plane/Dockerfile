FROM python:3.12-slim

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir .

EXPOSE 8002

CMD ["uvicorn", "app.api_main:app", "--host", "0.0.0.0", "--port", "8002"]

