import base64
from datetime import datetime, timezone
import json
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.auth import Principal, get_principal
from app.errors.cursor import encode_issue_cursor
from app.errors.models import ErrorEvent, Issue
from app.main import create_app


async def insert_issue(
    session_factory: async_sessionmaker[AsyncSession],
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    title: str = "Test Issue",
    status: str = "unresolved",
    level: str = "error",
    last_seen_at: datetime | None = None,
    first_seen_at: datetime | None = None,
    first_release: str | None = "v1.0.0",
    last_release: str | None = "v1.0.0",
    occurrence_count: int = 1,
) -> uuid.UUID:
    issue_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    first_seen = first_seen_at or now
    last_seen = last_seen_at or now

    async with session_factory() as session:
        issue = Issue(
            id=issue_id,
            workspace_id=workspace_id,
            project_id=project_id,
            fingerprint=uuid.uuid4().hex * 2,
            fingerprint_version=1,
            title=title,
            exception_type="TestException",
            culprit="app/test.py:run",
            level=level,
            status=status,
            first_seen_at=first_seen,
            last_seen_at=last_seen,
            occurrence_count=occurrence_count,
            affected_users_count=0,
            first_release=first_release,
            last_release=last_release,
        )
        session.add(issue)
        await session.commit()
    return issue_id


async def insert_event(
    session_factory: async_sessionmaker[AsyncSession],
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    issue_id: uuid.UUID,
    occurred_at: datetime | None = None,
    message: str = "event message",
    context: dict | None = None,
    stack_frames: list | None = None,
) -> uuid.UUID:
    event_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    occ = occurred_at or now

    async with session_factory() as session:
        event = ErrorEvent(
            id=event_id,
            workspace_id=workspace_id,
            project_id=project_id,
            issue_id=issue_id,
            fingerprint=uuid.uuid4().hex * 2,
            event_type="error",
            level="error",
            exception_type="TestException",
            message=message,
            stack_frames=stack_frames or [{"file": "test.py", "function": "bar", "line": 20, "in_app": True}],
            service="backend",
            route_template="/test",
            http_method="GET",
            status_code=500,
            environment="production",
            release="v1.0.0",
            user_hash="a" * 64,
            context=context or {"user_id": 123},
            occurred_at=occ,
            received_at=now,
        )
        session.add(event)
        await session.commit()
    return event_id


# =========================================================================
# Read Endpoints & Tenant Isolation Tests
# =========================================================================


@pytest.mark.asyncio
async def test_list_issues_tenant_and_project_scoped(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    test_workspace_id: uuid.UUID,
    test_project_id: uuid.UUID,
):
    # Issue in caller workspace & project
    target_id = await insert_issue(
        session_factory,
        workspace_id=test_workspace_id,
        project_id=test_project_id,
        title="Target Issue",
    )
    # Issue in caller workspace but different project
    other_proj_id = uuid.uuid4()
    await insert_issue(
        session_factory,
        workspace_id=test_workspace_id,
        project_id=other_proj_id,
        title="Other Project Issue",
    )
    # Issue in another workspace
    other_ws_id = uuid.uuid4()
    await insert_issue(
        session_factory,
        workspace_id=other_ws_id,
        project_id=test_project_id,
        title="Other Workspace Issue",
    )

    resp = await client.get(f"/api/v1/projects/{test_project_id}/issues")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == str(target_id)
    assert data["items"][0]["title"] == "Target Issue"
    assert data["meta"]["limit"] == 25
    assert data["meta"]["has_more"] is False
    assert data["meta"]["next_cursor"] is None

    # Verify no response body contains workspace_id or resolved_by
    assert "workspace_id" not in data["items"][0]
    assert "resolved_by" not in data["items"][0]


@pytest.mark.asyncio
async def test_other_workspace_issue_is_invisible_404(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    test_workspace_id: uuid.UUID,
    test_project_id: uuid.UUID,
):
    other_ws_id = uuid.uuid4()
    issue_b = await insert_issue(
        session_factory,
        workspace_id=other_ws_id,
        project_id=test_project_id,
        title="Workspace B Issue",
    )
    event_b = await insert_event(
        session_factory,
        workspace_id=other_ws_id,
        project_id=test_project_id,
        issue_id=issue_b,
    )

    # 1. Detail returns 404
    resp1 = await client.get(f"/api/v1/projects/{test_project_id}/issues/{issue_b}")
    assert resp1.status_code == 404
    assert resp1.json()["detail"] == "The requested resource was not found"

    # 2. Events list returns 404
    resp2 = await client.get(f"/api/v1/projects/{test_project_id}/issues/{issue_b}/events")
    assert resp2.status_code == 404
    assert resp2.json()["detail"] == "The requested resource was not found"

    # 3. Event detail returns 404
    resp3 = await client.get(f"/api/v1/projects/{test_project_id}/issues/{issue_b}/events/{event_b}")
    assert resp3.status_code == 404
    assert resp3.json()["detail"] == "The requested resource was not found"

    # 4. PATCH returns 404
    resp4 = await client.patch(
        f"/api/v1/projects/{test_project_id}/issues/{issue_b}",
        json={"status": "resolved"},
    )
    assert resp4.status_code == 404
    assert resp4.json()["detail"] == "The requested resource was not found"


@pytest.mark.asyncio
async def test_other_project_same_workspace_returns_404(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    test_workspace_id: uuid.UUID,
    test_project_id: uuid.UUID,
):
    project_2 = uuid.uuid4()
    issue_p2 = await insert_issue(
        session_factory,
        workspace_id=test_workspace_id,
        project_id=project_2,
        title="Project 2 Issue",
    )

    # Requesting issue_p2 through test_project_id in the URL path must 404
    resp_get = await client.get(f"/api/v1/projects/{test_project_id}/issues/{issue_p2}")
    assert resp_get.status_code == 404
    assert resp_get.json()["detail"] == "The requested resource was not found"

    resp_patch = await client.patch(
        f"/api/v1/projects/{test_project_id}/issues/{issue_p2}",
        json={"status": "resolved"},
    )
    assert resp_patch.status_code == 404
    assert resp_patch.json()["detail"] == "The requested resource was not found"


@pytest.mark.asyncio
async def test_event_belonging_to_another_issue_returns_404(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    test_workspace_id: uuid.UUID,
    test_project_id: uuid.UUID,
):
    issue_1 = await insert_issue(session_factory, test_workspace_id, test_project_id)
    issue_2 = await insert_issue(session_factory, test_workspace_id, test_project_id)
    event_of_issue_2 = await insert_event(session_factory, test_workspace_id, test_project_id, issue_2)

    # Requesting event_of_issue_2 under issue_1 path must return 404
    resp = await client.get(f"/api/v1/projects/{test_project_id}/issues/{issue_1}/events/{event_of_issue_2}")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "The requested resource was not found"


@pytest.mark.asyncio
async def test_status_filter_and_invalid_status_422(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    test_workspace_id: uuid.UUID,
    test_project_id: uuid.UUID,
):
    await insert_issue(session_factory, test_workspace_id, test_project_id, status="unresolved", title="Unresolved 1")
    await insert_issue(session_factory, test_workspace_id, test_project_id, status="resolved", title="Resolved 1")
    await insert_issue(session_factory, test_workspace_id, test_project_id, status="ignored", title="Ignored 1")

    # Filter unresolved
    resp_unres = await client.get(f"/api/v1/projects/{test_project_id}/issues?status=unresolved")
    assert resp_unres.status_code == 200
    items_unres = resp_unres.json()["items"]
    assert len(items_unres) == 1
    assert items_unres[0]["status"] == "unresolved"

    # Filter resolved
    resp_res = await client.get(f"/api/v1/projects/{test_project_id}/issues?status=resolved")
    assert resp_res.status_code == 200
    items_res = resp_res.json()["items"]
    assert len(items_res) == 1
    assert items_res[0]["status"] == "resolved"

    # Invalid status -> 422
    resp_invalid = await client.get(f"/api/v1/projects/{test_project_id}/issues?status=bad_status")
    assert resp_invalid.status_code == 422
    assert "detail" in resp_invalid.json()


@pytest.mark.asyncio
async def test_pagination_keyset_with_duplicate_last_seen_at(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    test_workspace_id: uuid.UUID,
    test_project_id: uuid.UUID,
):
    # Insert 5 issues: 3 sharing identical last_seen_at timestamp
    t_shared = datetime(2026, 10, 30, 10, 0, 0, tzinfo=timezone.utc)
    t_newer = datetime(2026, 10, 30, 11, 0, 0, tzinfo=timezone.utc)
    t_older = datetime(2026, 10, 30, 9, 0, 0, tzinfo=timezone.utc)

    id_newer = await insert_issue(session_factory, test_workspace_id, test_project_id, title="Newer", last_seen_at=t_newer)
    id_shared1 = await insert_issue(session_factory, test_workspace_id, test_project_id, title="Shared 1", last_seen_at=t_shared)
    id_shared2 = await insert_issue(session_factory, test_workspace_id, test_project_id, title="Shared 2", last_seen_at=t_shared)
    id_shared3 = await insert_issue(session_factory, test_workspace_id, test_project_id, title="Shared 3", last_seen_at=t_shared)
    id_older = await insert_issue(session_factory, test_workspace_id, test_project_id, title="Older", last_seen_at=t_older)

    # Page 1: limit=2
    resp_p1 = await client.get(f"/api/v1/projects/{test_project_id}/issues?limit=2")
    assert resp_p1.status_code == 200
    p1 = resp_p1.json()
    assert len(p1["items"]) == 2
    assert p1["meta"]["limit"] == 2
    assert p1["meta"]["has_more"] is True
    assert p1["meta"]["next_cursor"] is not None

    cursor1 = p1["meta"]["next_cursor"]

    # Page 2: limit=2 using cursor1
    resp_p2 = await client.get(f"/api/v1/projects/{test_project_id}/issues?limit=2&cursor={cursor1}")
    assert resp_p2.status_code == 200
    p2 = resp_p2.json()
    assert len(p2["items"]) == 2
    assert p2["meta"]["limit"] == 2
    assert p2["meta"]["has_more"] is True
    assert p2["meta"]["next_cursor"] is not None

    cursor2 = p2["meta"]["next_cursor"]

    # Page 3: limit=2 using cursor2
    resp_p3 = await client.get(f"/api/v1/projects/{test_project_id}/issues?limit=2&cursor={cursor2}")
    assert resp_p3.status_code == 200
    p3 = resp_p3.json()
    assert len(p3["items"]) == 1
    assert p3["meta"]["limit"] == 2
    assert p3["meta"]["has_more"] is False
    assert p3["meta"]["next_cursor"] is None

    # Collect all items and assert no duplicates and all 5 retrieved
    all_retrieved_ids = [item["id"] for item in p1["items"] + p2["items"] + p3["items"]]
    assert len(all_retrieved_ids) == 5
    assert len(set(all_retrieved_ids)) == 5
    expected_ids = {str(id_newer), str(id_shared1), str(id_shared2), str(id_shared3), str(id_older)}
    assert set(all_retrieved_ids) == expected_ids


@pytest.mark.asyncio
async def test_forged_cursor_with_other_tenant_id_does_not_leak(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    test_workspace_id: uuid.UUID,
    test_project_id: uuid.UUID,
):
    other_ws_id = uuid.uuid4()
    other_proj_id = uuid.uuid4()
    other_issue = await insert_issue(session_factory, other_ws_id, other_proj_id, title="Secret Issue")

    # Forged cursor containing other tenant's issue ID
    forged_cursor = encode_issue_cursor(datetime(2099, 1, 1, tzinfo=timezone.utc), other_issue)

    # Caller requests their own project with forged cursor
    resp = await client.get(f"/api/v1/projects/{test_project_id}/issues?cursor={forged_cursor}")
    assert resp.status_code == 200
    data = resp.json()
    # Does not leak other tenant's issue
    for it in data["items"]:
        assert it["id"] != str(other_issue)


@pytest.mark.asyncio
async def test_list_items_omit_stack_frames_and_context_while_detail_includes(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    test_workspace_id: uuid.UUID,
    test_project_id: uuid.UUID,
):
    issue_id = await insert_issue(session_factory, test_workspace_id, test_project_id)
    event_id = await insert_event(
        session_factory,
        test_workspace_id,
        test_project_id,
        issue_id,
        context={"secret": "hidden_in_list"},
        stack_frames=[{"file": "secret.py", "function": "fn", "line": 5, "in_app": True}],
    )

    # 1. Events list must NOT have stack_frames or context
    resp_list = await client.get(f"/api/v1/projects/{test_project_id}/issues/{issue_id}/events")
    assert resp_list.status_code == 200
    ev_item = resp_list.json()["items"][0]
    assert "stack_frames" not in ev_item
    assert "context" not in ev_item
    assert "workspace_id" not in ev_item

    # 2. Event detail DOES have stack_frames and context
    resp_detail = await client.get(f"/api/v1/projects/{test_project_id}/issues/{issue_id}/events/{event_id}")
    assert resp_detail.status_code == 200
    detail = resp_detail.json()
    assert "stack_frames" in detail
    assert "context" in detail
    assert detail["context"]["secret"] == "hidden_in_list"
    assert "workspace_id" not in detail


# =========================================================================
# PATCH Issue Status & Invariant Tests
# =========================================================================


@pytest.mark.asyncio
async def test_patch_resolve_and_verify_in_db(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    test_workspace_id: uuid.UUID,
    test_project_id: uuid.UUID,
    test_user_id: uuid.UUID,
):
    issue_id = await insert_issue(session_factory, test_workspace_id, test_project_id, status="unresolved")

    # PATCH to resolved
    resp = await client.patch(
        f"/api/v1/projects/{test_project_id}/issues/{issue_id}",
        json={"status": "resolved", "resolved_in_release": "v2.0.0"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "resolved"
    assert data["resolved_in_release"] == "v2.0.0"
    assert data["resolved_at"] is not None
    assert "resolved_by" not in data  # Never returned in response

    # Verify directly in DB
    async with session_factory() as session:
        stmt = select(Issue).where(Issue.id == issue_id)
        row = (await session.execute(stmt)).scalar_one()
        assert row.status == "resolved"
        assert row.resolved_in_release == "v2.0.0"
        assert row.resolved_at is not None
        assert row.resolved_by == test_user_id


@pytest.mark.asyncio
async def test_patch_ignore_and_unresolve_clears_resolved_fields(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    test_workspace_id: uuid.UUID,
    test_project_id: uuid.UUID,
):
    issue_id = await insert_issue(session_factory, test_workspace_id, test_project_id, status="unresolved")

    # 1. Resolve first
    await client.patch(
        f"/api/v1/projects/{test_project_id}/issues/{issue_id}",
        json={"status": "resolved", "resolved_in_release": "v1.0.0"},
    )

    # 2. Ignore clears fields
    resp_ignore = await client.patch(
        f"/api/v1/projects/{test_project_id}/issues/{issue_id}",
        json={"status": "ignored"},
    )
    assert resp_ignore.status_code == 200
    assert resp_ignore.json()["status"] == "ignored"
    assert resp_ignore.json()["resolved_at"] is None
    assert resp_ignore.json()["resolved_in_release"] is None

    async with session_factory() as session:
        row = (await session.execute(select(Issue).where(Issue.id == issue_id))).scalar_one()
        assert row.resolved_by is None
        assert row.resolved_at is None
        assert row.resolved_in_release is None

    # 3. Resolve again then unresolve
    await client.patch(
        f"/api/v1/projects/{test_project_id}/issues/{issue_id}",
        json={"status": "resolved"},
    )
    resp_unres = await client.patch(
        f"/api/v1/projects/{test_project_id}/issues/{issue_id}",
        json={"status": "unresolved"},
    )
    assert resp_unres.status_code == 200
    assert resp_unres.json()["status"] == "unresolved"
    assert resp_unres.json()["resolved_at"] is None

    async with session_factory() as session:
        row2 = (await session.execute(select(Issue).where(Issue.id == issue_id))).scalar_one()
        assert row2.resolved_by is None
        assert row2.resolved_at is None


@pytest.mark.asyncio
async def test_patch_idempotent_no_op(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    test_workspace_id: uuid.UUID,
    test_project_id: uuid.UUID,
):
    issue_id = await insert_issue(session_factory, test_workspace_id, test_project_id, status="unresolved")

    # Resolve
    resp1 = await client.patch(
        f"/api/v1/projects/{test_project_id}/issues/{issue_id}",
        json={"status": "resolved", "resolved_in_release": "v1.0.0"},
    )
    assert resp1.status_code == 200
    resolved_at_first = resp1.json()["resolved_at"]
    updated_at_first = resp1.json()["updated_at"]

    # Send exact same status again (idempotent no-op)
    resp2 = await client.patch(
        f"/api/v1/projects/{test_project_id}/issues/{issue_id}",
        json={"status": "resolved", "resolved_in_release": "v1.0.0"},
    )
    assert resp2.status_code == 200
    assert resp2.json()["resolved_at"] == resolved_at_first
    assert resp2.json()["updated_at"] == updated_at_first


@pytest.mark.asyncio
async def test_patch_never_touches_consumer_columns(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    test_workspace_id: uuid.UUID,
    test_project_id: uuid.UUID,
):
    t_first = datetime(2026, 10, 30, 8, 0, 0, tzinfo=timezone.utc)
    t_last = datetime(2026, 10, 30, 9, 0, 0, tzinfo=timezone.utc)
    issue_id = await insert_issue(
        session_factory,
        workspace_id=test_workspace_id,
        project_id=test_project_id,
        title="Original Title",
        first_seen_at=t_first,
        last_seen_at=t_last,
        first_release="v1.0.0",
        last_release="v1.5.0",
        occurrence_count=42,
    )

    async with session_factory() as session:
        orig = (await session.execute(select(Issue).where(Issue.id == issue_id))).scalar_one()
        orig_fp = orig.fingerprint
        orig_count = orig.occurrence_count
        orig_first_seen = orig.first_seen_at
        orig_last_seen = orig.last_seen_at
        orig_first_rel = orig.first_release
        orig_last_rel = orig.last_release
        orig_title = orig.title

    # Update status to resolved
    resp = await client.patch(
        f"/api/v1/projects/{test_project_id}/issues/{issue_id}",
        json={"status": "resolved"},
    )
    assert resp.status_code == 200

    async with session_factory() as session:
        after = (await session.execute(select(Issue).where(Issue.id == issue_id))).scalar_one()
        assert after.fingerprint == orig_fp
        assert after.occurrence_count == orig_count
        assert after.first_seen_at == orig_first_seen
        assert after.last_seen_at == orig_last_seen
        assert after.first_release == orig_first_rel
        assert after.last_release == orig_last_rel
        assert after.title == orig_title


@pytest.mark.asyncio
async def test_patch_on_other_workspace_returns_404_and_unchanged(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    test_workspace_id: uuid.UUID,
    test_project_id: uuid.UUID,
):
    other_ws = uuid.uuid4()
    other_issue = await insert_issue(session_factory, other_ws, test_project_id, status="unresolved")

    resp = await client.patch(
        f"/api/v1/projects/{test_project_id}/issues/{other_issue}",
        json={"status": "resolved"},
    )
    assert resp.status_code == 404

    # Verify other workspace issue was not modified
    async with session_factory() as session:
        row = (await session.execute(select(Issue).where(Issue.id == other_issue))).scalar_one()
        assert row.status == "unresolved"


# =========================================================================
# Query Parameter Validation & Auth Tests
# =========================================================================


@pytest.mark.asyncio
async def test_limit_validation(
    client: AsyncClient,
    test_project_id: uuid.UUID,
):
    # limit=0 -> 422
    resp0 = await client.get(f"/api/v1/projects/{test_project_id}/issues?limit=0")
    assert resp0.status_code == 422

    # limit=101 -> 422
    resp101 = await client.get(f"/api/v1/projects/{test_project_id}/issues?limit=101")
    assert resp101.status_code == 422

    # limit=abc -> 422
    resp_str = await client.get(f"/api/v1/projects/{test_project_id}/issues?limit=abc")
    assert resp_str.status_code == 422


@pytest.mark.asyncio
async def test_health_endpoint_unauthenticated(unauth_client: AsyncClient):
    resp = await unauth_client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_fail_closed_default_returns_401(
    unauth_client: AsyncClient,
    test_project_id: uuid.UUID,
):
    # Without any token
    resp_no_token = await unauth_client.get(f"/api/v1/projects/{test_project_id}/issues")
    assert resp_no_token.status_code == 401
    assert resp_no_token.json()["detail"] == "Missing or invalid credentials"

    # With a token (fail-closed implementation rejects all unverified tokens)
    resp_with_token = await unauth_client.get(
        f"/api/v1/projects/{test_project_id}/issues",
        headers={"Authorization": "Bearer some-token"},
    )
    assert resp_with_token.status_code == 401
    assert resp_with_token.json()["detail"] == "Missing or invalid credentials"


@pytest.mark.asyncio
async def test_token_without_workspace_claim_returns_403(
    session_factory: async_sessionmaker[AsyncSession],
    test_project_id: uuid.UUID,
):
    from fastapi import HTTPException, status
    app = create_app()

    # Simulate token valid for user, but lacking an active workspace claim
    async def _no_workspace_auth():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource",
        )

    app.dependency_overrides[get_principal] = _no_workspace_auth

    from httpx import ASGITransport, AsyncClient
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(f"/api/v1/projects/{test_project_id}/issues")
        assert resp.status_code == 403
        assert resp.json()["detail"] == "You do not have permission to access this resource"

