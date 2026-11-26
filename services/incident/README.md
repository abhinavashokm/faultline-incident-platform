# Faultline Incident Service

- `GET /health` reports process liveness.
- `GET /api/v1/projects/{project_id}/incidents` returns the project's incidents
  newest first. Each row includes `id`, `title`, `severity`, `status`,
  `assignee_id`, and `started_at`.
- `POST /api/v1/projects/{project_id}/incidents` creates an incident in the
  active workspace and returns its ID, title, severity, and status.
- `PATCH /api/v1/projects/{project_id}/incidents/{incident_id}/details` updates
  the incident's title, severity, and description. Send all three fields and
  use `null` to clear the description. Optionally send `related_issue_ids` to
  replace the linked issue set. An empty array removes all links. Omitting the
  field or sending `null` keeps the existing links. Newly linked issues must
  belong to the same project and workspace. Requires a Bearer access token and
  returns the ID, title, severity, and current status. Missing or inaccessible
  incidents return `404 Not Found`.
- `DELETE /api/v1/projects/{project_id}/incidents/{incident_id}` permanently
  removes the incident, its timeline entries, and its issue links in one
  transaction. The linked issues stay in Processing. Requires a Bearer access
  token and returns `204 No Content` on success or `404 Not Found` if the
  incident is missing or outside the authorized project and workspace.

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

The Compose migration job creates the Incident schema and tables before the
service starts. To rebuild and run the job against an existing Compose stack:

```sh
docker compose --profile backend run --rm --build migrate
```

For standalone development, create the Incident database first and run
`alembic -c services/incident/alembic.ini upgrade head` using the service
virtual environment and `INCIDENT_DATABASE_URL`.

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

The Compose backend profile exposes the endpoint through the gateway on port
`8000`. Run `docker compose --profile backend up -d --build gateway` and use
port `8000` in the creation request above. Compose mounts and reloads the
Incident application source during development. To recreate an existing
Incident container with that configuration, run:

```sh
docker compose --profile backend up -d --build incident
```

For a standalone gateway, enable
`GATEWAY_ENABLE_INCIDENT` and set `GATEWAY_UPSTREAM_INCIDENT_URL` to the
running service.

## Run in Docker

```sh
docker build -f services/incident/Dockerfile -t faultline-incident .
docker run --rm --env-file services/incident/.env -p 8004:8004 faultline-incident
```

Use upstream URLs reachable from the container.
