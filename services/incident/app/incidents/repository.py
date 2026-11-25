from sqlalchemy.ext.asyncio import AsyncSession

from app.incidents.models import Incident, IncidentIssue, IncidentTimelineEntry


class IncidentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def insert(self, incident: Incident) -> None:
        self.session.add(incident)
        await self.session.flush()

    def add_creation_details(
        self, entry: IncidentTimelineEntry, issues: list[IncidentIssue]
    ) -> None:
        self.session.add(entry)
        self.session.add_all(issues)
