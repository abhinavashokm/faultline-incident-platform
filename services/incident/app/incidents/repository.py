from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.incidents.models import Incident, IncidentIssue, IncidentTimelineEntry


class IncidentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_project(self, workspace_id: UUID, project_id: UUID) -> list[Incident]:
        query = (
            select(Incident)
            .where(Incident.workspace_id == workspace_id, Incident.project_id == project_id)
            .order_by(Incident.created_at.desc(), Incident.id.desc())
        )
        return list((await self.session.scalars(query)).all())

    async def insert(self, incident: Incident) -> None:
        self.session.add(incident)
        await self.session.flush()

    def add_creation_details(
        self, entry: IncidentTimelineEntry, issues: list[IncidentIssue]
    ) -> None:
        self.session.add(entry)
        self.session.add_all(issues)
