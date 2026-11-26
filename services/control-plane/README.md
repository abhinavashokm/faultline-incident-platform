# Faultline Control Plane

Control Plane service for workspace, project, user, and authentication management.

## Local Installation

From within `services/control-plane`:

```bash
pip install -e ../../libs/faultline-auth && pip install -e ".[dev]"
```

## Running Migrations

```bash
alembic upgrade head
```

## Running Tests

```bash
pytest
```


## Register a release from CI

Send `POST /api/v1/projects/{project_id}/releases` with
`Authorization: Bearer <project release token>`. Store the token in CI as
`FAULTLINE_RELEASE_TOKEN`. The request body contains `version` and
`commit_sha`, with an optional `artifact_ref`.

```json
{
  "version": "1.8.0",
  "commit_sha": "0123456789abcdef",
  "artifact_ref": "registry.example.com/my-app:1.8.0"
}
```

The response contains `id`, `version`, and `commit_sha`. A new release
returns `201`. An identical retry returns `200` with the same release ID.
Reusing a version with a different commit or artifact returns `409`.
An invalid, revoked, or expired token returns `401`. A token scoped to
another project or a request for an archived project returns `404`.
