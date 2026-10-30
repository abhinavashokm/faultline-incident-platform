import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.auth.security import create_access_token
from app.projects.models import Project, ProjectApiKey, ProjectSettings
from app.workspaces.models import Workspace, WorkspaceMember


async def setup_test_tenant(
    db_session: AsyncSession,
    role: str = "owner",
    email: str = "tenant_user@example.com",
    name: str = "Tenant User",
    ws_name: str = "Tenant Workspace",
    ws_slug: str = "tenant-workspace",
) -> tuple[User, Workspace, WorkspaceMember, dict[str, str]]:
    """Helper to create a user, workspace, and membership directly, returning auth headers."""
    user = User(
        id=uuid.uuid4(),
        email=email,
        full_name=name,
        password_hash="fake-hash",
        status="active",
    )
    workspace = Workspace(
        id=uuid.uuid4(),
        name=ws_name,
        slug=ws_slug,
        status="active",
        created_by=user.id,
    )
    member = WorkspaceMember(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        user_id=user.id,
        role=role,
        invited_by=None,
    )
    db_session.add_all([user, workspace, member])
    await db_session.commit()

    token = create_access_token(
        user_id=user.id,
        workspace_id=workspace.id,
        role=role,
    )
    headers = {"Authorization": f"Bearer {token}"}
    return user, workspace, member, headers


@pytest.mark.asyncio
async def test_create_project_success(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _, ws, user, headers = await setup_test_tenant(db_session, role="owner")

    payload = {
        "name": "Payments API",
        "slug": "payments-api",
        "platform": "python",
        "description": "Backend for payment processing",
    }
    resp = await client.post("/api/v1/projects", json=payload, headers=headers)
    assert resp.status_code == 201

    data = resp.json()
    assert data["name"] == "Payments API"
    assert data["slug"] == "payments-api"
    assert data["platform"] == "python"
    assert data["description"] == "Backend for payment processing"
    assert data["status"] == "active"
    assert "id" in data
    assert "dsn" in data
    assert data["dsn"].startswith("https://")
    assert f"@{data['id']}" in data["dsn"] or data["id"] in data["dsn"]

    project_id = uuid.UUID(data["id"])

    # Verify project in DB
    p_stmt = select(Project).where(Project.id == project_id)
    project = (await db_session.execute(p_stmt)).scalar_one()
    assert project.workspace_id == ws.id
    assert project.status == "active"
    assert project.archived_at is None
    assert project.archived_by is None

    # Verify project_settings created in same transaction
    s_stmt = select(ProjectSettings).where(ProjectSettings.project_id == project_id)
    settings = (await db_session.execute(s_stmt)).scalar_one()
    assert settings.workspace_id == ws.id
    assert settings.retention_days == 30
    assert settings.version == 1

    # Verify exactly one active ingest key created in same transaction
    k_stmt = select(ProjectApiKey).where(
        ProjectApiKey.project_id == project_id,
        ProjectApiKey.key_type == "ingest",
        ProjectApiKey.revoked_at.is_(None),
    )
    keys = (await db_session.execute(k_stmt)).scalars().all()
    assert len(keys) == 1
    assert keys[0].public_key is not None
    assert keys[0].key_hash is None
    assert keys[0].key_prefix is None


@pytest.mark.asyncio
async def test_create_project_validation_errors(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _, _, _, headers = await setup_test_tenant(db_session, role="owner")

    # Missing slug -> 422
    resp = await client.post(
        "/api/v1/projects", json={"name": "Valid Name"}, headers=headers
    )
    assert resp.status_code == 422

    # Invalid slug formats -> 422
    bad_slugs = [
        "Upper-Case",
        "spaces in slug",
        "slug_with_underscore",
        "-leading-hyphen",
        "trailing-hyphen-",
        "double--hyphen",
        "",
    ]
    for bad_slug in bad_slugs:
        resp = await client.post(
            "/api/v1/projects",
            json={"name": "Valid Name", "slug": bad_slug},
            headers=headers,
        )
        assert resp.status_code == 422

    # Missing name -> 422
    resp = await client.post(
        "/api/v1/projects", json={"slug": "valid-slug"}, headers=headers
    )
    assert resp.status_code == 422

    # Empty name -> 422
    resp = await client.post(
        "/api/v1/projects", json={"name": "", "slug": "valid-slug"}, headers=headers
    )
    assert resp.status_code == 422

    # Invalid platform -> 422
    resp = await client.post(
        "/api/v1/projects",
        json={"name": "Name", "slug": "valid-slug", "platform": "nodejs"},
        headers=headers,
    )
    assert resp.status_code == 422

    # Extra field -> 422
    resp = await client.post(
        "/api/v1/projects",
        json={"name": "Name", "slug": "valid-slug", "extra_field": "disallowed"},
        headers=headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_project_duplicate_slug_conflict(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _, _, _, headers = await setup_test_tenant(db_session, role="owner")

    payload = {"name": "First Project", "slug": "my-project"}
    resp1 = await client.post("/api/v1/projects", json=payload, headers=headers)
    assert resp1.status_code == 201

    resp2 = await client.post("/api/v1/projects", json=payload, headers=headers)
    assert resp2.status_code == 409
    assert (
        resp2.json()["detail"]
        == "A project with this slug already exists in the workspace"
    )


@pytest.mark.asyncio
async def test_list_and_get_projects_tenant_isolation_and_ordering(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _, _, _, headers1 = await setup_test_tenant(
        db_session, email="tenant1@example.com", ws_slug="ws-1"
    )
    _, _, _, headers2 = await setup_test_tenant(
        db_session, email="tenant2@example.com", ws_slug="ws-2"
    )

    # Create 2 projects in tenant 1
    resp_p1 = await client.post(
        "/api/v1/projects",
        json={"name": "Project 1", "slug": "project-1"},
        headers=headers1,
    )
    assert resp_p1.status_code == 201
    p1_id = resp_p1.json()["id"]

    resp_p2 = await client.post(
        "/api/v1/projects",
        json={"name": "Project 2", "slug": "project-2"},
        headers=headers1,
    )
    assert resp_p2.status_code == 201
    p2_id = resp_p2.json()["id"]

    # List projects in tenant 1 -> both present, ordered DESC by created_at, id
    list_resp = await client.get("/api/v1/projects", headers=headers1)
    assert list_resp.status_code == 200
    projects = list_resp.json()
    assert len(projects) == 2
    assert projects[0]["id"] == p2_id
    assert projects[1]["id"] == p1_id

    # List projects in tenant 2 -> empty
    list_resp2 = await client.get("/api/v1/projects", headers=headers2)
    assert list_resp2.status_code == 200
    assert list_resp2.json() == []

    # Get one: tenant 1 gets p1 -> 200
    get_resp = await client.get(f"/api/v1/projects/{p1_id}", headers=headers1)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == p1_id

    # Tenant 2 tries to get tenant 1's project -> 404 (never 403)
    get_resp_foreign = await client.get(
        f"/api/v1/projects/{p1_id}", headers=headers2
    )
    assert get_resp_foreign.status_code == 404
    assert get_resp_foreign.json()["detail"] == "Project not found"


@pytest.mark.asyncio
async def test_patch_project(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _, _, _, headers = await setup_test_tenant(db_session, role="owner")

    create_resp = await client.post(
        "/api/v1/projects",
        json={"name": "Original Name", "slug": "proj-patch", "description": "Desc"},
        headers=headers,
    )
    p_id = create_resp.json()["id"]

    # Valid name and description patch
    patch_resp = await client.patch(
        f"/api/v1/projects/{p_id}",
        json={"name": "Updated Name", "description": "New Desc"},
        headers=headers,
    )
    assert patch_resp.status_code == 200
    data = patch_resp.json()
    assert data["name"] == "Updated Name"
    assert data["description"] == "New Desc"
    assert data["slug"] == "proj-patch"

    # Valid patch: clearing description to None
    patch_resp2 = await client.patch(
        f"/api/v1/projects/{p_id}",
        json={"description": None},
        headers=headers,
    )
    assert patch_resp2.status_code == 200
    assert patch_resp2.json()["description"] is None

    # Disallowed fields -> 422
    for forbidden in [
        {"slug": "new-slug"},
        {"platform": "django"},
        {"status": "archived"},
        {"extra_field": 123},
    ]:
        resp = await client.patch(
            f"/api/v1/projects/{p_id}",
            json=forbidden,
            headers=headers,
        )
        assert resp.status_code == 422

    # Empty body -> 422
    empty_resp = await client.patch(
        f"/api/v1/projects/{p_id}",
        json={},
        headers=headers,
    )
    assert empty_resp.status_code == 422


@pytest.mark.asyncio
async def test_delete_project_soft_delete(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    user, _, _, headers = await setup_test_tenant(db_session, role="owner")

    create_resp = await client.post(
        "/api/v1/projects",
        json={"name": "To Delete", "slug": "delete-me"},
        headers=headers,
    )
    p_id = create_resp.json()["id"]

    # Delete project -> 204
    del_resp = await client.delete(f"/api/v1/projects/{p_id}", headers=headers)
    assert del_resp.status_code == 204
    assert del_resp.text == ""

    # GET -> 404
    get_resp = await client.get(f"/api/v1/projects/{p_id}", headers=headers)
    assert get_resp.status_code == 404

    # List -> absent
    list_resp = await client.get("/api/v1/projects", headers=headers)
    assert len(list_resp.json()) == 0

    # Slug cannot be reused (stay reserved) -> 409
    recreate_resp = await client.post(
        "/api/v1/projects",
        json={"name": "Reused Slug", "slug": "delete-me"},
        headers=headers,
    )
    assert recreate_resp.status_code == 409

    # Verify DB: status='archived', archived_at and archived_by are set
    p_stmt = select(Project).where(Project.id == uuid.UUID(p_id))
    project = (await db_session.execute(p_stmt)).scalar_one()
    assert project.status == "archived"
    assert project.archived_at is not None
    assert project.archived_by == user.id

    # Deleting already archived project -> 404
    del_again = await client.delete(f"/api/v1/projects/{p_id}", headers=headers)
    assert del_again.status_code == 404


@pytest.mark.asyncio
async def test_project_settings_lifecycle(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _, _, _, headers = await setup_test_tenant(db_session, role="owner")

    create_resp = await client.post(
        "/api/v1/projects",
        json={"name": "Settings Test", "slug": "settings-test"},
        headers=headers,
    )
    p_id = create_resp.json()["id"]

    # GET default settings
    get_resp = await client.get(
        f"/api/v1/projects/{p_id}/settings", headers=headers
    )
    assert get_resp.status_code == 200
    s_data = get_resp.json()
    assert s_data["project_id"] == p_id
    assert s_data["retention_days"] == 30
    assert s_data["ignored_status_codes"] == []
    assert s_data["version"] == 1
    assert "updated_at" in s_data

    # PATCH settings with de-duplication
    patch_payload = {
        "retention_days": 14,
        "ignored_status_codes": [400, 401, 403, 404, 400],
    }
    patch_resp = await client.patch(
        f"/api/v1/projects/{p_id}/settings",
        json=patch_payload,
        headers=headers,
    )
    assert patch_resp.status_code == 200
    patched = patch_resp.json()
    assert patched["retention_days"] == 14
    assert patched["ignored_status_codes"] == [400, 401, 403, 404]
    assert patched["version"] == 2

    # PATCH rate_limit_per_minute or unknown field -> 422
    bad_patch = await client.patch(
        f"/api/v1/projects/{p_id}/settings",
        json={"rate_limit_per_minute": 500},
        headers=headers,
    )
    assert bad_patch.status_code == 422

    bad_field = await client.patch(
        f"/api/v1/projects/{p_id}/settings",
        json={"unknown_field": "value"},
        headers=headers,
    )
    assert bad_field.status_code == 422

    # Empty body -> 422
    empty_patch = await client.patch(
        f"/api/v1/projects/{p_id}/settings",
        json={},
        headers=headers,
    )
    assert empty_patch.status_code == 422

    # Retention above max (default max is 90) -> 422
    over_max = await client.patch(
        f"/api/v1/projects/{p_id}/settings",
        json={"retention_days": 91},
        headers=headers,
    )
    assert over_max.status_code == 422

    # Retention below 1 -> 422
    below_min = await client.patch(
        f"/api/v1/projects/{p_id}/settings",
        json={"retention_days": 0},
        headers=headers,
    )
    assert below_min.status_code == 422


@pytest.mark.asyncio
async def test_project_api_key_lifecycle_and_rotation(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    _, _, _, headers = await setup_test_tenant(db_session, role="owner")

    create_resp = await client.post(
        "/api/v1/projects",
        json={"name": "Key Test", "slug": "key-test"},
        headers=headers,
    )
    p_id = create_resp.json()["id"]

    # GET active api key
    get_resp = await client.get(
        f"/api/v1/projects/{p_id}/api-key", headers=headers
    )
    assert get_resp.status_code == 200
    k_data = get_resp.json()
    assert k_data["key_type"] == "ingest"
    assert "dsn" in k_data
    assert "last_used_at" in k_data
    assert "created_at" in k_data
    # Assert secrets and internal fields are never returned
    assert "key_hash" not in k_data
    assert "key_prefix" not in k_data
    assert "name" not in k_data
    assert "expires_at" not in k_data
    assert "revoked_at" not in k_data

    old_key_id = k_data["id"]
    old_dsn = k_data["dsn"]

    # POST rotate api key
    rot_resp = await client.post(
        f"/api/v1/projects/{p_id}/api-key/rotate", headers=headers
    )
    assert rot_resp.status_code == 200
    new_data = rot_resp.json()
    assert new_data["id"] != old_key_id
    assert new_data["dsn"] != old_dsn

    # Verify database state after rotation
    all_keys_stmt = select(ProjectApiKey).where(
        ProjectApiKey.project_id == uuid.UUID(p_id)
    )
    all_keys = (await db_session.execute(all_keys_stmt)).scalars().all()
    assert len(all_keys) == 2

    # Exactly one active key
    active_keys = [k for k in all_keys if k.revoked_at is None]
    assert len(active_keys) == 1
    assert str(active_keys[0].id) == new_data["id"]

    # Old key is revoked
    revoked_keys = [k for k in all_keys if k.revoked_at is not None]
    assert len(revoked_keys) == 1
    assert str(revoked_keys[0].id) == old_key_id


@pytest.mark.asyncio
async def test_auth_and_permissions(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    # 1. Unauthenticated -> 401
    resp = await client.get("/api/v1/projects")
    assert resp.status_code == 401

    # 2. Setup owner and member in the same workspace
    _, ws, _, owner_headers = await setup_test_tenant(db_session, role="owner")

    # Create member in that workspace
    member_user = User(
        id=uuid.uuid4(),
        email="member@example.com",
        full_name="Member User",
        password_hash="fake-hash",
        status="active",
    )
    member_record = WorkspaceMember(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        user_id=member_user.id,
        role="member",
    )
    db_session.add_all([member_user, member_record])
    await db_session.commit()

    member_token = create_access_token(
        user_id=member_user.id,
        workspace_id=ws.id,
        role="member",
    )
    member_headers = {"Authorization": f"Bearer {member_token}"}

    # Owner creates a project
    create_resp = await client.post(
        "/api/v1/projects",
        json={"name": "Owner Project", "slug": "owner-proj"},
        headers=owner_headers,
    )
    assert create_resp.status_code == 201
    p_id = create_resp.json()["id"]

    # Member can READ:
    assert (
        await client.get("/api/v1/projects", headers=member_headers)
    ).status_code == 200
    assert (
        await client.get(f"/api/v1/projects/{p_id}", headers=member_headers)
    ).status_code == 200
    assert (
        await client.get(f"/api/v1/projects/{p_id}/settings", headers=member_headers)
    ).status_code == 200
    assert (
        await client.get(f"/api/v1/projects/{p_id}/api-key", headers=member_headers)
    ).status_code == 200

    # Member cannot MUTATE -> 403
    # POST project
    resp_create = await client.post(
        "/api/v1/projects",
        json={"name": "Member Project", "slug": "member-proj"},
        headers=member_headers,
    )
    assert resp_create.status_code == 403

    # PATCH project
    resp_patch = await client.patch(
        f"/api/v1/projects/{p_id}",
        json={"name": "Member Edit"},
        headers=member_headers,
    )
    assert resp_patch.status_code == 403

    # DELETE project
    resp_del = await client.delete(
        f"/api/v1/projects/{p_id}", headers=member_headers
    )
    assert resp_del.status_code == 403

    # PATCH settings
    resp_patch_s = await client.patch(
        f"/api/v1/projects/{p_id}/settings",
        json={"retention_days": 10},
        headers=member_headers,
    )
    assert resp_patch_s.status_code == 403

    # POST rotate api key
    resp_rot = await client.post(
        f"/api/v1/projects/{p_id}/api-key/rotate", headers=member_headers
    )
    assert resp_rot.status_code == 403


@pytest.mark.asyncio
async def test_db_check_constraints(
    db_session: AsyncSession,
) -> None:
    user, ws, _, _ = await setup_test_tenant(db_session, role="owner")
    now = datetime.now(timezone.utc)

    # 1. projects_archived_consistency_ck:
    # archived requires archived_at and archived_by NOT NULL
    async with db_session.begin_nested():
        bad_p1 = Project(
            id=uuid.uuid4(),
            workspace_id=ws.id,
            name="Bad Archived 1",
            slug="bad-arch-1",
            status="archived",
            archived_at=None,
            archived_by=None,
            created_by=user.id,
        )
        db_session.add(bad_p1)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    async with db_session.begin_nested():
        bad_p2 = Project(
            id=uuid.uuid4(),
            workspace_id=ws.id,
            name="Bad Archived 2",
            slug="bad-arch-2",
            status="archived",
            archived_at=now,
            archived_by=None,
            created_by=user.id,
        )
        db_session.add(bad_p2)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    async with db_session.begin_nested():
        # active requires archived_at and archived_by NULL
        bad_p3 = Project(
            id=uuid.uuid4(),
            workspace_id=ws.id,
            name="Bad Active",
            slug="bad-act",
            status="active",
            archived_at=now,
            archived_by=user.id,
            created_by=user.id,
        )
        db_session.add(bad_p3)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    # Valid active project
    good_p = Project(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        name="Good Active",
        slug="good-act",
        status="active",
        archived_at=None,
        archived_by=None,
        created_by=user.id,
    )
    db_session.add(good_p)
    await db_session.flush()

    # 2. project_api_keys_key_type_consistency_ck:
    # ingest requires public_key NOT NULL and key_hash, key_prefix NULL
    async with db_session.begin_nested():
        bad_k1 = ProjectApiKey(
            id=uuid.uuid4(),
            workspace_id=ws.id,
            project_id=good_p.id,
            key_type="ingest",
            public_key=None,
            key_hash=None,
            key_prefix=None,
            created_by=user.id,
        )
        db_session.add(bad_k1)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    async with db_session.begin_nested():
        bad_k2 = ProjectApiKey(
            id=uuid.uuid4(),
            workspace_id=ws.id,
            project_id=good_p.id,
            key_type="ingest",
            public_key="pub123",
            key_hash="a" * 64,
            key_prefix=None,
            created_by=user.id,
        )
        db_session.add(bad_k2)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    # release requires key_hash, key_prefix NOT NULL and public_key NULL
    async with db_session.begin_nested():
        bad_k3 = ProjectApiKey(
            id=uuid.uuid4(),
            workspace_id=ws.id,
            project_id=good_p.id,
            key_type="release",
            public_key=None,
            key_hash=None,
            key_prefix="pref",
            created_by=user.id,
        )
        db_session.add(bad_k3)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    async with db_session.begin_nested():
        bad_k4 = ProjectApiKey(
            id=uuid.uuid4(),
            workspace_id=ws.id,
            project_id=good_p.id,
            key_type="release",
            public_key="pub123",
            key_hash="a" * 64,
            key_prefix="pref",
            created_by=user.id,
        )
        db_session.add(bad_k4)
        with pytest.raises(IntegrityError):
            await db_session.flush()

    # Valid ingest key
    good_ingest = ProjectApiKey(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        project_id=good_p.id,
        key_type="ingest",
        public_key="pub123",
        key_hash=None,
        key_prefix=None,
        created_by=user.id,
    )
    db_session.add(good_ingest)
    await db_session.flush()

    # Valid release key
    good_release = ProjectApiKey(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        project_id=good_p.id,
        key_type="release",
        public_key=None,
        key_hash="a" * 64,
        key_prefix="pref",
        created_by=user.id,
    )
    db_session.add(good_release)
    await db_session.flush()


@pytest.mark.asyncio
async def test_all_five_mutating_endpoints_through_app_success(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Verify all 5 mutating endpoints succeed through real ASGITransport without session transaction conflicts."""
    _, _, _, headers = await setup_test_tenant(db_session, role="owner")

    # 1. POST /api/v1/projects (create_project)
    create_payload = {
        "name": "Pipeline Service",
        "slug": "pipeline-service",
        "platform": "fastapi",
        "description": "Initial description",
    }
    create_resp = await client.post(
        "/api/v1/projects", json=create_payload, headers=headers
    )
    assert create_resp.status_code == 201
    p_data = create_resp.json()
    project_id = p_data["id"]
    assert p_data["name"] == "Pipeline Service"
    assert "dsn" in p_data

    # 2. PATCH /api/v1/projects/{id} (update_project)
    patch_proj_resp = await client.patch(
        f"/api/v1/projects/{project_id}",
        json={"name": "Pipeline Service Updated", "description": "New description"},
        headers=headers,
    )
    assert patch_proj_resp.status_code == 200
    assert patch_proj_resp.json()["name"] == "Pipeline Service Updated"
    assert patch_proj_resp.json()["description"] == "New description"

    # 3. PATCH /api/v1/projects/{id}/settings (update_settings)
    patch_sett_resp = await client.patch(
        f"/api/v1/projects/{project_id}/settings",
        json={"retention_days": 45, "ignored_status_codes": [404, 500]},
        headers=headers,
    )
    assert patch_sett_resp.status_code == 200
    sett_data = patch_sett_resp.json()
    assert sett_data["retention_days"] == 45
    assert sett_data["ignored_status_codes"] == [404, 500]
    assert sett_data["version"] == 2

    # 4. POST /api/v1/projects/{id}/api-key/rotate (rotate_api_key)
    rotate_resp = await client.post(
        f"/api/v1/projects/{project_id}/api-key/rotate", headers=headers
    )
    assert rotate_resp.status_code == 200
    rot_data = rotate_resp.json()
    assert rot_data["key_type"] == "ingest"
    assert "dsn" in rot_data

    # 5. DELETE /api/v1/projects/{id} (delete_project)
    delete_resp = await client.delete(
        f"/api/v1/projects/{project_id}", headers=headers
    )
    assert delete_resp.status_code == 204
    assert delete_resp.text == ""

    # Verify project is now archived (GET returns 404)
    get_resp = await client.get(
        f"/api/v1/projects/{project_id}", headers=headers
    )
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_failed_mutations_leave_no_writes(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Verify that failed mutations (409 conflict, 403 forbidden, 404 not found) roll back cleanly and leave no writes."""
    _, ws, _, owner_headers = await setup_test_tenant(db_session, role="owner")

    # Member in the same workspace
    member_user = User(
        id=uuid.uuid4(),
        email="regular_member@example.com",
        full_name="Regular Member",
        password_hash="fake-hash",
        status="active",
    )
    member_record = WorkspaceMember(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        user_id=member_user.id,
        role="member",
    )
    db_session.add_all([member_user, member_record])
    await db_session.commit()

    member_token = create_access_token(
        user_id=member_user.id,
        workspace_id=ws.id,
        role="member",
    )
    member_headers = {"Authorization": f"Bearer {member_token}"}

    # 1. Create a successful project first
    init_resp = await client.post(
        "/api/v1/projects",
        json={"name": "Existing Project", "slug": "dup-slug"},
        headers=owner_headers,
    )
    assert init_resp.status_code == 201
    existing_id = uuid.UUID(init_resp.json()["id"])

    # Count rows before failed create
    projects_before = (
        await db_session.execute(
            select(Project).where(Project.workspace_id == ws.id)
        )
    ).scalars().all()
    settings_before = (
        await db_session.execute(
            select(ProjectSettings).where(ProjectSettings.workspace_id == ws.id)
        )
    ).scalars().all()
    keys_before = (
        await db_session.execute(
            select(ProjectApiKey).where(ProjectApiKey.workspace_id == ws.id)
        )
    ).scalars().all()

    assert len(projects_before) == 1
    assert len(settings_before) == 1
    assert len(keys_before) == 1

    # Part A: Duplicate slug failure (409) must roll back and leave no project, settings or api-key rows
    fail_create_resp = await client.post(
        "/api/v1/projects",
        json={"name": "Ghost Project", "slug": "dup-slug"},
        headers=owner_headers,
    )
    assert fail_create_resp.status_code == 409

    # Assert no new project, settings, or key was saved in DB
    ghost_project = (
        await db_session.execute(
            select(Project).where(Project.name == "Ghost Project")
        )
    ).scalar_one_or_none()
    assert ghost_project is None

    projects_after = (
        await db_session.execute(
            select(Project).where(Project.workspace_id == ws.id)
        )
    ).scalars().all()
    settings_after = (
        await db_session.execute(
            select(ProjectSettings).where(ProjectSettings.workspace_id == ws.id)
        )
    ).scalars().all()
    keys_after = (
        await db_session.execute(
            select(ProjectApiKey).where(ProjectApiKey.workspace_id == ws.id)
        )
    ).scalars().all()

    assert len(projects_after) == 1
    assert len(settings_after) == 1
    assert len(keys_after) == 1

    # Part B: 403 Forbidden mutations must leave no writes
    # Member attempts create -> 403
    forbidden_create = await client.post(
        "/api/v1/projects",
        json={"name": "Forbidden Project", "slug": "forbidden-slug"},
        headers=member_headers,
    )
    assert forbidden_create.status_code == 403
    p_check = (
        await db_session.execute(
            select(Project).where(Project.slug == "forbidden-slug")
        )
    ).scalar_one_or_none()
    assert p_check is None

    # Member attempts update project -> 403
    forbidden_update = await client.patch(
        f"/api/v1/projects/{existing_id}",
        json={"name": "Hacked Name"},
        headers=member_headers,
    )
    assert forbidden_update.status_code == 403
    existing_p = (
        await db_session.execute(
            select(Project).where(Project.id == existing_id)
        )
    ).scalar_one()
    assert existing_p.name == "Existing Project"

    # Member attempts update settings -> 403
    forbidden_settings = await client.patch(
        f"/api/v1/projects/{existing_id}/settings",
        json={"retention_days": 1},
        headers=member_headers,
    )
    assert forbidden_settings.status_code == 403
    existing_s = (
        await db_session.execute(
            select(ProjectSettings).where(ProjectSettings.project_id == existing_id)
        )
    ).scalar_one()
    assert existing_s.retention_days == 30
    assert existing_s.version == 1

    # Member attempts rotate key -> 403
    forbidden_rot = await client.post(
        f"/api/v1/projects/{existing_id}/api-key/rotate",
        headers=member_headers,
    )
    assert forbidden_rot.status_code == 403
    active_keys = (
        await db_session.execute(
            select(ProjectApiKey).where(
                ProjectApiKey.project_id == existing_id,
                ProjectApiKey.revoked_at.is_(None),
            )
        )
    ).scalars().all()
    assert len(active_keys) == 1

    # Member attempts delete -> 403
    forbidden_del = await client.delete(
        f"/api/v1/projects/{existing_id}",
        headers=member_headers,
    )
    assert forbidden_del.status_code == 403
    await db_session.refresh(existing_p)
    assert existing_p.status == "active"

    # Part C: 404 Not Found mutations must leave no writes
    random_id = uuid.uuid4()
    assert (
        await client.patch(
            f"/api/v1/projects/{random_id}",
            json={"name": "Nonexistent"},
            headers=owner_headers,
        )
    ).status_code == 404

    assert (
        await client.delete(
            f"/api/v1/projects/{random_id}", headers=owner_headers
        )
    ).status_code == 404

    assert (
        await client.patch(
            f"/api/v1/projects/{random_id}/settings",
            json={"retention_days": 10},
            headers=owner_headers,
        )
    ).status_code == 404

    assert (
        await client.post(
            f"/api/v1/projects/{random_id}/api-key/rotate",
            headers=owner_headers,
        )
    ).status_code == 404


