import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_alert_rules_empty(client: AsyncClient, test_project_id: uuid.UUID):
    response = await client.get(f"/api/v1/projects/{test_project_id}/alert-rules")
    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "meta": {"limit": 25, "has_more": False, "next_cursor": None},
    }


@pytest.mark.asyncio
async def test_create_and_list_alert_rule(client: AsyncClient, test_project_id: uuid.UUID):
    # Create notification channel first
    ch_res = await client.post(
        f"/api/v1/projects/{test_project_id}/notification-channels",
        json={
            "name": "Dev Team",
            "channel_type": "email",
            "destination": "devs@faultline.io",
            "enabled": True,
        },
    )
    assert ch_res.status_code == 201
    channel_id = ch_res.json()["id"]

    # Create alert rule
    rule_payload = {
        "name": "New Issue Alert",
        "rule_type": "new_issue",
        "conditions": {},
        "severity": "critical",
        "environment": "production",
        "enabled": True,
        "channel_ids": [channel_id],
    }

    create_res = await client.post(
        f"/api/v1/projects/{test_project_id}/alert-rules",
        json=rule_payload,
    )
    assert create_res.status_code == 201
    created_data = create_res.json()
    assert created_data["name"] == "New Issue Alert"
    assert created_data["rule_type"] == "new_issue"
    assert created_data["severity"] == "critical"
    assert created_data["environment"] == "production"
    assert created_data["enabled"] is True
    assert len(created_data["channels"]) == 1
    assert created_data["channels"][0]["id"] == channel_id
    assert created_data["channels"][0]["name"] == "Dev Team"

    rule_id = created_data["id"]

    # List alert rules
    list_res = await client.get(f"/api/v1/projects/{test_project_id}/alert-rules")
    assert list_res.status_code == 200
    rules = list_res.json()["items"]
    assert len(rules) >= 1
    assert any(r["id"] == rule_id for r in rules)

    # Toggle / update alert rule
    update_res = await client.patch(
        f"/api/v1/projects/{test_project_id}/alert-rules/{rule_id}",
        json={"enabled": False},
    )
    assert update_res.status_code == 200
    assert update_res.json()["enabled"] is False

    # Delete alert rule
    del_res = await client.delete(
        f"/api/v1/projects/{test_project_id}/alert-rules/{rule_id}"
    )
    assert del_res.status_code == 204

    # Verify deleted
    list_after_res = await client.get(f"/api/v1/projects/{test_project_id}/alert-rules")
    assert list_after_res.status_code == 200
    assert not any(r["id"] == rule_id for r in list_after_res.json()["items"])


@pytest.mark.asyncio
async def test_list_alert_rules_cursor(client: AsyncClient, test_project_id: uuid.UUID) -> None:
    path = f"/api/v1/projects/{test_project_id}/alert-rules"
    ids = []
    for name in ("First", "Second"):
        created = await client.post(path, json={"name": name, "rule_type": "new_issue"})
        assert created.status_code == 201
        ids.append(created.json()["id"])

    response = await client.get(path, params={"limit": 1})
    assert response.status_code == 200
    first = response.json()
    assert [rule["id"] for rule in first["items"]] == ids[1:]
    assert first["meta"]["has_more"] is True
    assert first["meta"]["next_cursor"]

    response = await client.get(path, params={"limit": 1, "cursor": first["meta"]["next_cursor"]})
    assert response.status_code == 200
    second = response.json()
    assert [rule["id"] for rule in second["items"]] == ids[:1]
    assert second["meta"] == {"limit": 1, "has_more": False, "next_cursor": None}

    invalid = await client.get(path, params={"cursor": "invalid"})
    assert invalid.status_code == 422
    assert invalid.json() == {"detail": "Invalid cursor"}
    assert (await client.get(path, params={"limit": 101})).status_code == 422
