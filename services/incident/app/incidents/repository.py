from uuid import UUID

from sqlalchemy import delete, select
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

    async def get_for_project(
        self, workspace_id: UUID, project_id: UUID, incident_id: UUID, *, for_update: bool = False
    ) -> Incident | None:
        query = select(Incident).where(
            Incident.workspace_id == workspace_id,
            Incident.project_id == project_id,
            Incident.id == incident_id,
        )
        if for_update:
            query = query.with_for_update()
        return await self.session.scalar(query)

    async def list_related_issues(self, incident_id: UUID) -> list[IncidentIssue]:
        query = (
            select(IncidentIssue)
            .where(IncidentIssue.incident_id == incident_id)
            .order_by(IncidentIssue.snapshot_at, IncidentIssue.id)
        )
        return list((await self.session.scalars(query)).all())

    async def list_timeline(self, incident_id: UUID) -> list[IncidentTimelineEntry]:
        query = (
            select(IncidentTimelineEntry)
            .where(IncidentTimelineEntry.incident_id == incident_id)
            .order_by(IncidentTimelineEntry.created_at.desc(), IncidentTimelineEntry.id.desc())
        )
        return list((await self.session.scalars(query)).all())

    async def delete_incident(self, incident: Incident) -> None:
        await self.session.execute(
            delete(IncidentIssue).where(IncidentIssue.incident_id == incident.id)
        )
        await self.session.execute(
            delete(IncidentTimelineEntry).where(IncidentTimelineEntry.incident_id == incident.id)
        )
        await self.session.delete(incident)

    async def insert(self, incident: Incident) -> None:
        self.session.add(incident)
        await self.session.flush()

    def add_creation_details(
        self, entry: IncidentTimelineEntry, issues: list[IncidentIssue]
    ) -> None:
        self.session.add(entry)
        self.session.add_all(issues)
