# Faultline API Gateway (`services/gateway`)

The API Gateway is a high-performance, **routing-only** edge reverse proxy for the Faultline platform. It forwards external HTTP client and SDK traffic to the appropriate upstream internal services based on path prefix matching.

---

## Architectural Principles & Security Boundaries

### 1. Routing Only — No Authentication or Authorization
- **Authentication stays in each individual service**: Every downstream service verifies user access tokens locally via `libs/faultline-auth` using public keys obtained from the Control Plane JWKS endpoint (`/.well-known/jwks.json`).
- The Gateway **never** inspects, validates, parses, or decodes JWT access tokens or refresh tokens.
- The Gateway contains **no database**, no SQLAlchemy models, no Alembic migrations, and **no business logic**.

### 2. Header Forwarding & Anti-Spoofing Rules
- **Preserved Credential Headers**: The `Authorization` header (`Bearer <jwt>`) and SDK project credential headers (`X-Faultline-Key`, `X-Project-Key`) are forwarded byte-for-byte unchanged to upstreams.
- **Stripped Client Identity Headers**: To prevent untrusted clients from spoofing identity to internal services, the Gateway strictly strips:
  - `X-User-Id`
  - `X-Workspace-Id`
  - `X-Principal*` (e.g. `X-Principal-User`, `X-Principal-Role`)
  - `X-Forwarded-User`
  - `X-Role`
- **Stripped Hop-by-Hop Headers**: Strips standard hop-by-hop headers (`Connection`, `Keep-Alive`, `Proxy-Authenticate`, `Proxy-Authorization`, `TE`, `Trailers`, `Transfer-Encoding`, `Upgrade`) and `Host`.
- **Injected Tracing & Forwarding Headers**:
  - `X-Request-ID`: Reuses valid incoming ID (alphanumeric/hyphen/dot up to 64 chars) or generates a UUID4. Propagated to response and upstream request.
  - `X-Forwarded-Proto`: Client scheme (`http` / `https`).
  - `X-Forwarded-For`: Appends client socket IP (or preserves chain only if `GATEWAY_TRUST_FORWARDED_FOR=true`).

---

## Route Table

Routing uses longest-prefix matching. If no route matches, the Gateway returns `404 {"detail": "Not found"}`. Unknown paths are never forwarded to a default service.

| Path Prefix | Target Upstream | Default Base URL | Description |
|---|---|---|---|
| `/.well-known/jwks.json` | `control-plane` | `http://control-plane:8000` | Public JWKS keys for JWT verification |
| `/api/v1/auth` | `control-plane` | `http://control-plane:8000` | Signup, login, refresh, logout, user profile |
| `/api/v1/workspaces` | `control-plane` | `http://control-plane:8000` | Workspace management |
| `/api/v1/projects/{project_id}/issues` | `processing` | `http://processing-api:8002` | Issue lists, details, events, status updates |
| `/api/v1/projects` | `control-plane` | `http://control-plane:8000` | Project CRUD, API keys, and project settings |
| `/api/v1/events` | `ingestion` | `http://ingestion:8001` | SDK error event intake |
| `/api/v1/projects/{project_id}/alerts` | `alerting` | `http://alerting:8003` | *Disabled* (Service not yet implemented) |
| `/api/v1/projects/{project_id}/incidents` | `incident` | `http://incident:8004` | *Disabled* (Service not yet implemented) |
| `/api/v1/projects/{project_id}/investigations` | `investigation` | `http://investigation:8005` | *Disabled* (Service not yet implemented) |

---

## Health Checks

- `GET /health`: Liveness probe for the Gateway. Returns `200 {"status": "ok"}` immediately without querying upstreams. Exempt from rate limiting.
- `GET /health/upstreams`: Probes each configured upstream's `/health` or `/healthz` endpoint with a 1.5s timeout. Returns 200 (healthy) or 503 (degraded). Never leaks upstream URLs or internal error details.

---

## Error Responses

All error responses return standardized JSON:
- `404 Not Found`: `{"detail": "Not found"}`
- `413 Payload Too Large`: `{"detail": "Request body too large"}`
- `429 Too Many Requests`: `{"detail": "Too many requests"}` (includes `Retry-After` header)
- `502 Bad Gateway`: `{"detail": "Upstream unavailable"}` (logged with internal reason)
- `504 Gateway Timeout`: `{"detail": "Upstream timeout"}` (logged with internal reason)

---

## Environment Variables

All settings use the `GATEWAY_` prefix:

| Variable | Default | Description |
|---|---|---|
| `GATEWAY_UPSTREAM_CONTROL_PLANE_URL` | `http://control-plane:8000` | Control plane base URL |
| `GATEWAY_UPSTREAM_INGESTION_URL` | `http://ingestion:8001` | Ingestion base URL |
| `GATEWAY_UPSTREAM_PROCESSING_URL` | `http://processing-api:8002` | Processing base URL |
| `GATEWAY_CORS_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Allowed CORS origins |
| `GATEWAY_RATE_LIMIT_REQUESTS` | `120` | Max requests per IP in window |
| `GATEWAY_RATE_LIMIT_WINDOW_SECONDS` | `60` | Rate limit window duration |
| `GATEWAY_RATE_LIMIT_STRATEGY` | `auto` | Rate limit backend: `auto`, `redis`, or `memory` |
| `GATEWAY_REDIS_URL` | `redis://redis:6379/0` | Redis connection URL |
| `GATEWAY_CONNECT_TIMEOUT_SECONDS` | `3.0` | Upstream connection timeout |
| `GATEWAY_READ_TIMEOUT_SECONDS` | `30.0` | Default upstream read timeout |
| `GATEWAY_INGESTION_READ_TIMEOUT_SECONDS` | `30.0` | Ingestion-specific read timeout |
| `GATEWAY_MAX_REQUEST_BODY_BYTES` | `5242880` (5 MB) | Max request payload size |
| `GATEWAY_TRUST_FORWARDED_FOR` | `false` | Whether to trust incoming `X-Forwarded-For` |
| `GATEWAY_POOL_MAX_CONNECTIONS` | `100` | Max client connection pool size |
| `GATEWAY_POOL_MAX_KEEPALIVE_CONNECTIONS` | `20` | Max keepalive connections |
| `GATEWAY_LOG_LEVEL` | `INFO` | Structured logging level |

---

## Running Locally

### With virtualenv:
```bash
cd services/gateway
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### With Docker Compose:
```bash
docker compose up -d --build gateway
curl http://localhost:8000/health
```

### Running Tests:
```bash
cd services/gateway
pytest tests/
```

