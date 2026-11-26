from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from faultline_auth import Principal, get_principal
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.core.db import get_session
from app.incidents.models import Incident, IncidentTimelineEntry
from app.main import create_app


class IncidentStatusAPITests(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.principal = Principal(user_id=uuid4(), workspace_id=uuid4())
        self.incident = Incident(
            id=uuid4(),
            workspace_id=self.principal.workspace_id,
            status="mitigated",
            resolved_at=None,
        )
        self.session = MagicMock(spec=AsyncSession)
        self.session.scalar = AsyncMock(side_effect=self.find_incident)
        app = create_app()
        app.state.http_client = None
        app.state.settings = None
        async def principal() -> Principal:
            return self.principal

        async def session() -> AsyncSession:
            return self.session

        app.dependency_overrides[get_principal] = principal
        app.dependency_overrides[get_session] = session
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
        self.addAsyncCleanup(self.client.aclose)
        self.path = f"/api/v1/incidents/{self.incident.id}/status"

    async def find_incident(self, query: Select[tuple[Incident]]) -> Incident | None:
        compiled = query.compile(dialect=postgresql.dialect())
        sql = str(compiled)
        self.assertIn("WHERE incidents.incidents.workspace_id = ", sql)
        self.assertIn("AND incidents.incidents.id = ", sql)
        self.assertTrue(sql.endswith("FOR UPDATE"))
        self.session.begin.return_value.__aenter__.assert_awaited()

        if set(compiled.params.values()) == {self.incident.workspace_id, self.incident.id}:
            return self.incident
        return None

    async def test_resolution_and_reopening_return_200_and_record_timeline(self) -> None:
        response = await self.client.post(self.path, json={"status": "resolved", "note": "Recovery verified"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "id": str(self.incident.id),
            "status": "resolved",
            "resolved_at": self.incident.resolved_at.isoformat() + "+00:00",
        })
        entry = self.session.add.call_args.args[0]
        self.assertIsInstance(entry, IncidentTimelineEntry)
        self.assertEqual(entry.actor_id, self.principal.user_id)
        self.assertEqual(entry.incident_id, self.incident.id)
        self.assertEqual(entry.event_type, "incident_status_changed")
        self.assertEqual(entry.created_at, self.incident.resolved_at)
        self.assertEqual(entry.event_metadata, {
            "old_status": "mitigated",
            "new_status": "resolved",
            "note": "Recovery verified",
        })
        self.session.begin.return_value.__aexit__.assert_awaited_once_with(None, None, None)

        response = await self.client.post(self.path, json={"status": "open"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "open")
        self.assertIsNone(response.json()["resolved_at"])
        self.assertIsNone(self.incident.resolved_at)

    async def test_missing_and_outside_workspace_return_404(self) -> None:
        cases = (
            (f"/api/v1/incidents/{uuid4()}/status", self.principal.workspace_id),
            (self.path, uuid4()),
        )
        for path, workspace_id in cases:
            with self.subTest(path=path):
                self.incident.workspace_id = workspace_id
                response = await self.client.post(path, json={"status": "resolved"})
                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.json(), {"detail": "Incident not found"})
        self.session.add.assert_not_called()

    async def test_invalid_and_same_status_return_409_without_writing(self) -> None:
        for target, detail in (
            ("open", "Cannot move incident from mitigated to open."),
            ("mitigated", "Incident is already mitigated."),
        ):
            with self.subTest(target=target):
                response = await self.client.post(self.path, json={"status": target})
                self.assertEqual(response.status_code, 409)
                self.assertEqual(response.json(), {"detail": detail})
        self.assertEqual(self.incident.status, "mitigated")
        self.assertIsNone(self.incident.resolved_at)
        self.session.add.assert_not_called()

    async def test_acknowledged_is_rejected(self) -> None:
        response = await self.client.post(self.path, json={"status": "acknowledged"})
        self.assertEqual(response.status_code, 422)
        self.session.scalar.assert_not_awaited()
