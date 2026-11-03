# faultline-auth

Shared authentication library for the Faultline error tracking and incident response platform.

Provides verify-only RS256 JWT access token verification for FastAPI microservices. The library verifies tokens locally using JWKS or static public keys without per-request roundtrips to the Control Plane.

## Features

- **Local Verification:** Verifies RS256 signatures, `exp`, `iat`, `iss`, `aud`, `jti`, and `type` claims.
- **JWKS & Static Providers:** Caching with TTL and refetch cooldown for JWKS, or single-read static PEM public keys.
- **Process-wide Cached Verifier:** Reuses `TokenVerifier` instances across requests without rebuilding.
- **FastAPI Integration:**
  - `configure_auth()`: Validates configuration at application startup (lifespan) to fail fast on misconfiguration.
  - `get_principal`: FastAPI dependency extracting `Principal(user_id, workspace_id, session_id, role)`. Enforces presence of active `workspace_id`.
  - `AuthDependencies`: Low-level dependencies (`current_user`, `require_workspace`, `require_role`).
- **Standardized Error Policy:** Generic client-facing error details that never leak internal exception strings.

## Environment Variables

All settings are configured via environment variables prefixed with `AUTH_`:

| Variable | Type | Default | Description |
|---|---|---|---|
| `AUTH_PROVIDER` | `str` | *Required* | Key provider type: `"jwks"` or `"static"` |
| `AUTH_ISSUER` | `str` | *Required* | Expected JWT issuer (`iss`), e.g. `"faultline-control-plane"` |
| `AUTH_AUDIENCE` | `str` | *Required* | Expected JWT audience (`aud`), e.g. `"faultline"` |
| `AUTH_JWKS_URL` | `str` | *Required for jwks* | Control Plane JWKS endpoint URL (e.g. `http://control-plane:8000/.well-known/jwks.json`) |
| `AUTH_PUBLIC_KEY_PATH` | `str` | *Required for static* | Path to RSA public key PEM file (e.g. `keys/public.pem`) |
| `AUTH_JWT_KEY_ID` | `str` | *Required for static* | Key ID (`kid`) matching token headers (e.g. `"dev-1"`) |
| `AUTH_LEEWAY_SECONDS` | `int` | `30` | Clock-skew leeway in seconds for exp/iat |
| `AUTH_JWKS_CACHE_TTL_SECONDS` | `int` | `300` | TTL in seconds for cached JWKS public keys |
| `AUTH_JWKS_REFETCH_COOLDOWN_SECONDS` | `int` | `30` | Minimum cooldown between remote JWKS refetches on unknown `kid` |
| `AUTH_JWKS_TIMEOUT_SECONDS` | `float` | `3.0` | HTTP request timeout in seconds when fetching JWKS |

*(Backwards compatibility: If an `AUTH_*` variable is unset, `PROCESSING_AUTH_*` is checked as fallback.)*

## Error Policy

| Situation | HTTP Status | Headers | Client `detail` |
|---|---|---|---|
| Missing, non-Bearer, or empty credentials | `401 Unauthorized` | `WWW-Authenticate: Bearer` | `"Missing or invalid credentials"` |
| Invalid token (bad signature, expired, wrong iss/aud/alg, unknown kid) | `401 Unauthorized` | `WWW-Authenticate: Bearer` | `"Missing or invalid credentials"` |
| Invalid workspace claim (present but not a valid UUID) | `403 Forbidden` | — | `"You do not have permission to access this resource"` |
| Key provider failure (`KeysUnavailable`) | `503 Service Unavailable` | — | `"Authentication temporarily unavailable"` |
| Misconfiguration at request time (`AuthConfigurationError`) | `500 Internal Server Error` | — | `"Internal server error"` |
| Valid token without `workspace_id` in `get_principal` | `403 Forbidden` | — | `"You do not have permission to access this resource"` |

Server logs details (`logger.debug` for client-side token errors, `logger.error` for unavailable keys or server misconfiguration) without exposing internals to the client.

## Quickstart

### Service Startup (FastAPI Lifespan)

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from faultline_auth import configure_auth

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fails fast at boot if AUTH_* environment variables are invalid or keys missing
    configure_auth()
    yield

app = FastAPI(lifespan=lifespan)
```

### Route Dependency

```python
from fastapi import APIRouter, Depends
from faultline_auth import Principal, get_principal

router = APIRouter()

@router.get("/issues")
async def list_issues(principal: Principal = Depends(get_principal)):
    # principal.workspace_id and principal.user_id are verified UUIDs
    return await issue_service.list(workspace_id=principal.workspace_id)
```

