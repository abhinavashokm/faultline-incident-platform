# Faultline Python SDK (`faultline-sdk`)

The official Python client library for the Faultline Error Tracking & Incident Response Platform.

## Features

- **Zero Runtime Dependencies**: Built entirely on the Python Standard Library (`urllib`, `threading`, `queue`).
- **Resilient & Non-Blocking**: Sending runs in a single background daemon thread with a bounded queue. Internal failures never crash or block the host application.
- **Automatic Data Sanitization**: Built-in redaction for authorization headers, session cookies, passwords, tokens, API keys, and credit card numbers.
- **FastAPI / ASGI Integration**: Generic ASGI middleware and a thin FastAPI wrapper for normalized route templates and request telemetry.
- **Global Unhandled Error Capture**: Intercepts unhandled errors across `sys.excepthook` and `threading.excepthook` without breaking existing handlers.

## Installation

```bash
pip install faultline-sdk
```

For local development inside the monorepo:

```bash
pip install -e sdk/python
```

## Quick Start

### Basic Usage

```python
import faultline

# 1. Initialize the SDK
faultline.init(
    dsn="https://<project_api_key>@errors.example.com",
    release="v1.8.0",          # If omitted, reads from os.environ['APP_RELEASE']
    environment="production",  # Defaults to "production"
    service="order-service",   # Optional service identifier
)

# 2. Capture caught exceptions
try:
    risky_operation()
except Exception as exc:
    faultline.capture_exception(exc)

# 3. Capture custom messages
faultline.capture_message("Rate limit threshold approaching", level="warning")

# 4. Flush and close on shutdown
faultline.flush(timeout=2.0)
faultline.close()
```

### FastAPI Integration

```python
from fastapi import FastAPI
import faultline
from faultline.integrations.fastapi import FaultlineFastAPIMiddleware

faultline.init(
    dsn="https://<project_api_key>@errors.example.com",
    environment="production",
)

app = FastAPI()

# Add Faultline middleware (normalizes route templates, captures errors & performance)
app.add_middleware(FaultlineFastAPIMiddleware)

@app.get("/items/{item_id}")
async def get_item(item_id: int):
    if item_id == 0:
        raise ValueError("Invalid item id")
    return {"item_id": item_id}
```

### Generic ASGI Integration

```python
import faultline
from faultline.integrations.asgi import FaultlineASGIMiddleware

faultline.init(dsn="https://<project_api_key>@errors.example.com")

# Wrap any ASGI 3 application
app = FaultlineASGIMiddleware(my_asgi_app)
```

## Configuration

| Parameter | Environment Variable | Default | Description |
|---|---|---|---|
| `dsn` | - | *Required* | Project DSN: `https://<project_api_key>@<host>` |
| `release` | `APP_RELEASE` | `None` | Application release version (e.g., git tag or commit SHA) |
| `environment` | - | `"production"` | Deployment environment (`production`, `staging`, etc.) |
| `service` | - | `None` | Logical service name |
| `max_queue_size` | - | `1000` | Maximum number of events buffered in memory |
| `max_retries` | - | `3` | Maximum retry attempts for transient server errors (5xx/network) |
| `timeout` | - | `5.0` | HTTP request timeout in seconds |
| `flush_timeout` | - | `2.0` | Default timeout for `flush()` and `close()` |

## Running Tests

From repository root:

```bash
PYTHONPATH=sdk/python/src python3 -m pytest sdk/python/tests/
```

