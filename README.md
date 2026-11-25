# Faultline

Faultline is a multi-tenant error tracking and alerting platform. A Python SDK sends application exceptions and endpoint telemetry to an ingestion API. Kafka workers group related exceptions into issues and aggregate performance metrics for a Next.js dashboard. Alerting evaluates newly created issues against project rules and queues notifications.

The repository contains the SDK, gateway, Control Plane, ingestion, processing, and alerting. Incident management, investigation, and human-approved remediation are planned.

## Try the SDK-to-issue flow

1. Follow the [local setup guide](docs/docker.md), then run `make up` and `make ps`.
2. Open the dashboard at <http://localhost:3000>, sign up, and use [Mailpit](http://localhost:8025) to retrieve the verification code. Create a project and open its SDK setup page to get the project API key.
3. From the repo root in a Python 3.12 virtual environment, install the SDK and send an exception. Replace `PROJECT_API_KEY` with the key from your project.

   ```bash
   python -m pip install -e sdk/python
   FAULTLINE_DSN='http://PROJECT_API_KEY@localhost:8000' python - <<'PY'
   import os

   import faultline

   faultline.init(dsn=os.environ["FAULTLINE_DSN"], environment="development")
   try:
       raise RuntimeError("Faultline quickstart error")
   except RuntimeError as exc:
       faultline.capture_exception(exc)
   finally:
       faultline.flush(timeout=10.0)
       faultline.close()
   PY
   ```

4. Open the project's **Issues** view and look for `Faultline quickstart error`. Allow time for the processing worker to consume the event. Run the same snippet again and refresh to see a second occurrence grouped under the same issue.

## Documentation

- [Architecture](docs/architecture.md) explains the service boundaries, tenant checks, and Kafka failure behavior.
- [Local setup and API docs](docs/docker.md) covers Compose, keys, migrations, and local service URLs.
- [Kafka event contracts](docs/events.md) lists producers, consumers, partition keys, and schemas.
- [Verification](docs/verification.md) covers replay, offset handling, and tenant isolation checks.
- [Python SDK](sdk/python/README.md) covers SDK configuration and ASGI integration.
