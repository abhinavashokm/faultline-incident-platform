# Faultline Incident Service

The service scaffold exposes `GET /health` for process liveness.

## Run locally

From the repository root, create a virtual environment, install the service, and start it.

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -e services/incident
.venv/bin/python -m uvicorn app.main:app --app-dir services/incident --port 8004
```

`curl --fail http://localhost:8004/health` returns `{"status":"ok"}`.

## Run in Docker

```sh
docker build -f services/incident/Dockerfile -t faultline-incident .
docker run --rm -p 8004:8004 faultline-incident
```

## Incident persistence

Incidents are project-scoped within the workspace from the verified JWT.
The project-scoped API needs an approved `project_id` column on
`incidents.incidents` before persistence is added.
