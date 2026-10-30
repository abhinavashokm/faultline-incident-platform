import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.auth.security import create_access_token
from app.core.config import settings
from app.projects.models import Project, ProjectApiKey
from app.workspaces.models import Workspace

TEST_INTERNAL_SECRET = "test-internal-service-secret-12345"


@pytest.fixture(autouse=True)
def configure_internal_secret() -> None:
    original = settings.internal_service_secret
    settings.internal_service_secret = TEST_INTERNAL_SECRET
    yield
    settings.internal_service_secret = original


async def create_fixture_tenant(
    db_session: AsyncSession,
    workspace_status: str = "active",
    project_status: str = "active",
    key_type: str = "ingest",
    public_key: str | None = "test_ingest_key_abcdef123456",
    revoked: bool = False,
) -> tuple[User, Workspace, Project, ProjectApiKey]:
    now = datetime.now(timezone.utc)
    user = User(
        id=uuid.uuid4(),
        email=f"user_{uuid.uuid4().hex[:8]}@example.com",
        full_name="Internal Test User",
        password_hash="fake-hash",
        status="active",
    )
    workspace = Workspace(
        id=uuid.uuid4(),
        name="Internal Test Workspace",
        slug=f"ws-{uuid.uuid4().hex[:8]}",
        status=workspace_status,
        created_by=user.id,
    )

    archived_at = now if project_status == "archived" else None
    archived_by = user.id if project_status == "archived" else None

    project = Project(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        name="Internal Test Project",
        slug=f"proj-{uuid.uuid4().hex[:8]}",
        status=project_status,
        archived_at=archived_at,
        archived_by=archived_by,
        created_by=user.id,
    )

    if key_type == "ingest":
        api_key = ProjectApiKey(
            id=uuid.uuid4(),
            workspace_id=workspace.id,
            project_id=project.id,
            key_type="ingest",
            public_key=public_key,
            key_hash=None,
            key_prefix=None,
            revoked_at=now if revoked else None,
            created_by=user.id,
        )
    else:
        # release key: requires key_hash, key_prefix and public_key=None
        api_key = ProjectApiKey(
            id=uuid.uuid4(),
            workspace_id=workspace.id,
            project_id=project.id,
            key_type="release",
            public_key=None,
            key_hash="b" * 64,
            key_prefix="fl_rel_",
            revoked_at=now if revoked else None,
            created_by=user.id,
        )

    db_session.add(user)
    await db_session.flush()
    db_session.add(workspace)
    await db_session.flush()
    db_session.add(project)
    await db_session.flush()
    db_session.add(api_key)
    await db_session.commit()
    return user, workspace, project, api_key


@pytest.mark.asyncio
async def test_resolve_key_valid_ingest_key(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    pub_key = "valid_ingest_key_9876543210"
    _, ws, proj, _ = await create_fixture_tenant(
        db_session,
        workspace_status="active",
        project_status="active",
        key_type="ingest",
        public_key=pub_key,
        revoked=False,
    )

    headers = {"X-Service-Token": TEST_INTERNAL_SECRET}
    resp = await client.get(
        f"/api/v1/internal/project-keys/{pub_key}",
        headers=headers,
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["workspace_id"] == str(ws.id)
    assert data["project_id"] == str(proj.id)
    assert data["key_type"] == "ingest"
    assert data["active"] is True


@pytest.mark.asyncio
async def test_resolve_key_unknown_key(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    headers = {"X-Service-Token": TEST_INTERNAL_SECRET}
    resp = await client.get(
        "/api/v1/internal/project-keys/nonexistent_key_12345",
        headers=headers,
    )

    assert resp.status_code == 404
    data = resp.json()
    assert data["detail"] == "Project key not found"


@pytest.mark.asyncio
async def test_resolve_key_revoked_key(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    pub_key = "revoked_ingest_key_11111"
    await create_fixture_tenant(
        db_session,
        workspace_status="active",
        project_status="active",
        key_type="ingest",
        public_key=pub_key,
        revoked=True,
    )

    headers = {"X-Service-Token": TEST_INTERNAL_SECRET}
    resp = await client.get(
        f"/api/v1/internal/project-keys/{pub_key}",
        headers=headers,
    )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Project key not found"


@pytest.mark.asyncio
async def test_resolve_key_release_type_key_value_passed(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    # Set up a project with only a release key (hash="b"*64, prefix="fl_rel_")
    _, _, _, release_key = await create_fixture_tenant(
        db_session,
        workspace_status="active",
        project_status="active",
        key_type="release",
        revoked=False,
    )

    headers = {"X-Service-Token": TEST_INTERNAL_SECRET}

    # Test passing key_prefix as public_key
    resp_prefix = await client.get(
        f"/api/v1/internal/project-keys/{release_key.key_prefix}",
        headers=headers,
    )
    assert resp_prefix.status_code == 404
    assert resp_prefix.json()["detail"] == "Project key not found"

    # Test passing key_hash as public_key
    resp_hash = await client.get(
        f"/api/v1/internal/project-keys/{release_key.key_hash}",
        headers=headers,
    )
    assert resp_hash.status_code == 404
    assert resp_hash.json()["detail"] == "Project key not found"


@pytest.mark.asyncio
async def test_resolve_key_archived_project(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    pub_key = "archived_proj_key_22222"
    await create_fixture_tenant(
        db_session,
        workspace_status="active",
        project_status="archived",
        key_type="ingest",
        public_key=pub_key,
        revoked=False,
    )

    headers = {"X-Service-Token": TEST_INTERNAL_SECRET}
    resp = await client.get(
        f"/api/v1/internal/project-keys/{pub_key}",
        headers=headers,
    )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Project key not found"


@pytest.mark.asyncio
async def test_resolve_key_suspended_workspace(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    pub_key = "suspended_ws_key_33333"
    await create_fixture_tenant(
        db_session,
        workspace_status="suspended",
        project_status="active",
        key_type="ingest",
        public_key=pub_key,
        revoked=False,
    )

    headers = {"X-Service-Token": TEST_INTERNAL_SECRET}
    resp = await client.get(
        f"/api/v1/internal/project-keys/{pub_key}",
        headers=headers,
    )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Project key not found"


@pytest.mark.asyncio
async def test_resolve_key_deleted_workspace(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    pub_key = "deleted_ws_key_44444"
    await create_fixture_tenant(
        db_session,
        workspace_status="deleted",
        project_status="active",
        key_type="ingest",
        public_key=pub_key,
        revoked=False,
    )

    headers = {"X-Service-Token": TEST_INTERNAL_SECRET}
    resp = await client.get(
        f"/api/v1/internal/project-keys/{pub_key}",
        headers=headers,
    )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Project key not found"


@pytest.mark.asyncio
async def test_resolve_key_missing_service_secret(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    pub_key = "any_key_55555"
    # No X-Service-Token header
    resp = await client.get(f"/api/v1/internal/project-keys/{pub_key}")

    assert resp.status_code == 401
    assert "Missing or invalid service token" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_resolve_key_wrong_service_secret(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    pub_key = "any_key_66666"
    headers = {"X-Service-Token": "incorrect-secret-value"}
    resp = await client.get(
        f"/api/v1/internal/project-keys/{pub_key}",
        headers=headers,
    )

    assert resp.status_code == 401
    assert "Missing or invalid service token" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_resolve_key_unconfigured_service_secret(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    settings.internal_service_secret = ""
    pub_key = "any_key_77777"
    headers = {"X-Service-Token": TEST_INTERNAL_SECRET}
    resp = await client.get(
        f"/api/v1/internal/project-keys/{pub_key}",
        headers=headers,
    )

    assert resp.status_code == 401
    assert "Missing or invalid service token" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_resolve_key_rejects_user_jwt(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Verifies user JWTs cannot be used to authenticate internal endpoints."""
    user, ws, _, _ = await create_fixture_tenant(
        db_session,
        public_key="jwt_test_key_88888",
    )
    user_jwt = create_access_token(
        user_id=user.id,
        workspace_id=ws.id,
        role="owner",
    )

    # Passing user JWT in Authorization header without X-Service-Token -> 401
    resp = await client.get(
        "/api/v1/internal/project-keys/jwt_test_key_88888",
        headers={"Authorization": f"Bearer {user_jwt}"},
    )
    assert resp.status_code == 401

    # Passing user JWT in X-Service-Token -> 401
    resp2 = await client.get(
        "/api/v1/internal/project-keys/jwt_test_key_88888",
        headers={"X-Service-Token": user_jwt},
    )
    assert resp2.status_code == 401


@pytest.mark.asyncio
async def test_resolve_key_response_contains_only_four_fields(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    pub_key = "exact_fields_key_99999"
    _, ws, proj, key = await create_fixture_tenant(
        db_session,
        workspace_status="active",
        project_status="active",
        key_type="ingest",
        public_key=pub_key,
        revoked=False,
    )

    headers = {"X-Service-Token": TEST_INTERNAL_SECRET}
    resp = await client.get(
        f"/api/v1/internal/project-keys/{pub_key}",
        headers=headers,
    )

    assert resp.status_code == 200
    data = resp.json()

    # Verify exact set of fields
    expected_fields = {"workspace_id", "project_id", "key_type", "active"}
    assert set(data.keys()) == expected_fields

    # Verify values
    assert data["workspace_id"] == str(ws.id)
    assert data["project_id"] == str(proj.id)
    assert data["key_type"] == "ingest"
    assert data["active"] is True

    # Explicitly ensure sensitive/internal columns are NOT present
    for forbidden in (
        "id",
        "key_hash",
        "key_prefix",
        "public_key",
        "created_by",
        "user_id",
        "last_used_at",
        "expires_at",
        "revoked_at",
        "created_at",
    ):
        assert forbidden not in data
