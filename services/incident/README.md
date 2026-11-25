# Faultline Incident Service

- `GET /health` reports process liveness.
- `POST /api/v1/projects/{project_id}/incidents` creates an incident in the
  active workspace and returns its ID, title, severity, and status.

Creation requires a Bearer access token, a title, and a severity. The request
can include a description, related issue IDs, and the caller's own user ID
as the assignee. The service checks project access through Control Plane and
checks each related issue through Processing. It writes the incident, issue
links, and creation timeline entry in one transaction.

## Configuration

Set these variables in the environment or local `.env` file.

- `INCIDENT_DATABASE_URL` is the async PostgreSQL URL for the Incident database.
- `INCIDENT_CONTROL_PLANE_URL` is the Control Plane API base URL.
- `INCIDENT_PROCESSING_URL` is the Processing API base URL.
- Use the shared auth settings `AUTH_PROVIDER`, `AUTH_JWKS_URL` (for JWKS),
  `AUTH_ISSUER`, and `AUTH_AUDIENCE`.

Before sending creation requests, provision the `incidents` schema and apply
an Incident-owned migration for `incidents`, `incident_issues`, and
`incident_timeline` using the approved DBML. The incident table requires
`project_id` and an index on `(workspace_id, project_id, created_at)`. For an
existing incident table, backfill project IDs before enforcing `NOT NULL`.
Once the Incident Alembic configuration and migration are in place, run
`alembic upgrade head` from the Incident service directory.

## Run locally

From the repository root, create a service-specific virtual environment and run:

```sh
python3.12 -m venv services/incident/.venv
services/incident/.venv/bin/python -m pip install -e libs/faultline-auth -e services/incident
services/incident/.venv/bin/python -m uvicorn app.main:app --app-dir services/incident --port 8004
```

```sh
curl --fail http://localhost:8004/health
curl --fail-with-body -X POST "http://localhost:8004/api/v1/projects/${PROJECT_ID}/incidents" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"title":"Payment processing failures","severity":"high"}'
```

The gateway can expose the same endpoint when `GATEWAY_ENABLE_INCIDENT` is
enabled and `GATEWAY_UPSTREAM_INCIDENT_URL` points to the running service.

## Run in Docker

```sh
docker build -f services/incident/Dockerfile -t faultline-incident .
docker run --rm --env-file services/incident/.env -p 8004:8004 faultline-incident
```

Use upstream URLs reachable from the container.
