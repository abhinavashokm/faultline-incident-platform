import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_alert_rules_empty(client: AsyncClient, test_project_id: uuid.UUID):
    response = await client.get(f"/api/v1/projects/{test_project_id}/alert-rules")
    assert response.status_code == 200
    assert response.json() == []


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
    rules = list_res.json()
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
    assert not any(r["id"] == rule_id for r in list_after_res.json())

