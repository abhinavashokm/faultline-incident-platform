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

