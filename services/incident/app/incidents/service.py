import logging
from datetime import datetime, timezone
from uuid import UUID

import httpx
from fastapi import HTTPException
from faultline_auth import Principal
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.incidents.models import Incident, IncidentIssue, IncidentTimelineEntry
from app.incidents.repository import IncidentRepository
from app.incidents.schemas import (
    CreatedIncident,
    CreateIncidentRequest,
    IncidentDetail,
    IncidentListItem,
    IncidentStatus,
    IssueSnapshot,
    RelatedIssue,
    TimelineEntry,
    UpdateIncidentDetailsRequest,
    UpdateIncidentStatusRequest,
    UpdatedIncidentStatus,
)

logger = logging.getLogger(__name__)


_NEXT_STATUS: dict[str, IncidentStatus] = {
    "open": "investigating",
    "investigating": "mitigated",
    "mitigated": "resolved",
    "resolved": "open",
}


def validate_status_transition(current: str, target: IncidentStatus) -> None:
    if current == target:
        raise HTTPException(409, f"Incident is already {target}.")
    if _NEXT_STATUS.get(current) != target:
        raise HTTPException(409, f"Cannot move incident from {current} to {target}.")


def as_utc_naive(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


class IncidentService:
    def __init__(
        self, session: AsyncSession, client: httpx.AsyncClient, settings: Settings
    ) -> None:
        self.session = session
        self.repository = IncidentRepository(session)
        self.client = client
        self.settings = settings

    async def _get_resource(
        self, url: str, token: str, resource: str
    ) -> httpx.Response:
        try:
            response = await self.client.get(url, headers={"Authorization": f"Bearer {token}"})
        except httpx.RequestError as exc:
            logger.warning("Incident %s lookup failed (%s)", resource, type(exc).__name__)
            raise HTTPException(503, "Resource verification temporarily unavailable") from exc
        if response.status_code in (403, 404):
            raise HTTPException(404, f"{resource} not found")
        if response.status_code != 200:
            logger.warning("Incident %s lookup returned %s", resource, response.status_code)
            raise HTTPException(503, "Resource verification temporarily unavailable")
        return response

    async def _verify_project(self, project_id: UUID, token: str) -> None:
        control_plane = str(self.settings.control_plane_url).rstrip("/")
        await self._get_resource(f"{control_plane}/api/v1/projects/{project_id}", token, "Project")

    async def _load_issue_snapshots(
        self, project_id: UUID, issue_ids: list[UUID], token: str
    ) -> list[IssueSnapshot]:
        project_path = f"/api/v1/projects/{project_id}"
        processing = str(self.settings.processing_url).rstrip("/")
        snapshots: list[IssueSnapshot] = []
        for issue_id in dict.fromkeys(issue_ids):
            response = await self._get_resource(
                f"{processing}{project_path}/issues/{issue_id}", token, "Issue"
            )
            try:
                snapshot = IssueSnapshot.model_validate_json(response.content)
                if snapshot.id != issue_id:
                    raise ValueError("Issue ID mismatch")
            except ValueError as exc:
                logger.warning("Incident issue lookup returned an invalid snapshot")
                raise HTTPException(503, "Resource verification temporarily unavailable") from exc
            snapshots.append(snapshot)

        return snapshots

    @staticmethod
    def _issue_link(incident_id: UUID, issue: IssueSnapshot) -> IncidentIssue:
        return IncidentIssue(
            incident_id=incident_id,
            issue_id=issue.id,
            issue_title=issue.title[:255],
            error_type=issue.exception_type[:255] if issue.exception_type else None,
            first_seen_at=as_utc_naive(issue.first_seen),
            last_seen_at=as_utc_naive(issue.last_seen),
            occurrence_count=issue.occurrence_count,
        )

    async def list_for_project(
        self, project_id: UUID, principal: Principal, token: str
    ) -> list[IncidentListItem]:
        await self._verify_project(project_id, token)
        incidents = await self.repository.list_for_project(principal.workspace_id, project_id)
        return [IncidentListItem.model_validate(incident) for incident in incidents]

    async def get_detail(
        self, project_id: UUID, incident_id: UUID, principal: Principal, token: str
    ) -> IncidentDetail:
        await self._verify_project(project_id, token)
        incident = await self.repository.get_for_project(
            principal.workspace_id, project_id, incident_id
        )
        if incident is None:
            raise HTTPException(404, "Incident not found")

        issues = await self.repository.list_related_issues(incident.id)
        timeline = await self.repository.list_timeline(incident.id)
        return IncidentDetail(
            id=incident.id,
            title=incident.title,
            severity=incident.severity,
            status=incident.status,
            assigned_to=incident.assigned_to,
            started_at=incident.started_at,
            description=incident.description,
            related_issues=[RelatedIssue.model_validate(issue) for issue in issues],
            timeline=[TimelineEntry.model_validate(entry) for entry in timeline],
        )

    async def update_status(
        self, incident_id: UUID, payload: UpdateIncidentStatusRequest, principal: Principal
    ) -> UpdatedIncidentStatus:
        async with self.session.begin():
            incident = await self.repository.get_for_workspace_for_update(
                principal.workspace_id, incident_id
            )
            if incident is None:
                raise HTTPException(404, "Incident not found")

            old_status = incident.status
            new_status = payload.status
            validate_status_transition(old_status, new_status)

            now = as_utc_naive(datetime.now(timezone.utc))
            incident.status = new_status
            incident.updated_at = now
            if new_status == "resolved":
                incident.resolved_at = now
            elif new_status == "open":
                incident.resolved_at = None

            message = f"Status changed from {old_status} to {new_status}."
            if payload.note:
                message = f"{message} {payload.note}"
            self.repository.add_timeline_entry(
                IncidentTimelineEntry(
                    incident_id=incident.id,
                    actor_id=principal.user_id,
                    event_type="incident_status_changed",
                    message=message,
                    event_metadata={
                        "old_status": old_status,
                        "new_status": new_status,
                        "note": payload.note,
                    },
                    created_at=now,
                )
            )
            return UpdatedIncidentStatus(
                id=incident.id, status=new_status, resolved_at=incident.resolved_at
            )

    async def update_details(
        self,
        project_id: UUID,
        incident_id: UUID,
        payload: UpdateIncidentDetailsRequest,
        principal: Principal,
        token: str,
    ) -> CreatedIncident:
        await self._verify_project(project_id, token)
        async with self.session.begin():
            incident = await self.repository.get_for_project(
                principal.workspace_id, project_id, incident_id, for_update=True
            )
            if incident is None:
                raise HTTPException(404, "Incident not found")

            links_changed = False
            if payload.related_issue_ids is not None:
                links_changed = await self._sync_issue_links(
                    project_id, incident.id, payload.related_issue_ids, token
                )
            incident.title = payload.title
            incident.severity = payload.severity
            incident.description = payload.description
            if links_changed or self.session.is_modified(incident):
                incident.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
            return CreatedIncident.model_validate(incident)

    async def _sync_issue_links(
        self, project_id: UUID, incident_id: UUID, issue_ids: list[UUID], token: str
    ) -> bool:
        current = {
            link.issue_id: link for link in await self.repository.list_related_issues(incident_id)
        }
        requested = dict.fromkeys(issue_ids)
        removed = [link for issue_id, link in current.items() if issue_id not in requested]
        new_ids = [issue_id for issue_id in requested if issue_id not in current]
        if not removed and not new_ids:
            return False

        snapshots = await self._load_issue_snapshots(project_id, new_ids, token)
        await self.repository.update_issue_links(
            removed, [self._issue_link(incident_id, issue) for issue in snapshots]
        )
        return True

    async def delete_incident(
        self, project_id: UUID, incident_id: UUID, principal: Principal, token: str
    ) -> None:
        await self._verify_project(project_id, token)
        async with self.session.begin():
            incident = await self.repository.get_for_project(
                principal.workspace_id, project_id, incident_id, for_update=True
            )
            if incident is None:
                raise HTTPException(404, "Incident not found")

            await self.repository.delete_incident(incident)

    async def create(
        self, project_id: UUID, payload: CreateIncidentRequest, principal: Principal, token: str
    ) -> CreatedIncident:
        await self._verify_project(project_id, token)

        # The MVP supports self-assignment within the verified active workspace.
        if payload.assignee_id is not None and payload.assignee_id != principal.user_id:
            raise HTTPException(404, "Assignee not found")

        snapshots = await self._load_issue_snapshots(project_id, payload.related_issue_ids, token)

        async with self.session.begin():
            incident = Incident(
                workspace_id=principal.workspace_id,
                project_id=project_id,
                title=payload.title,
                description=payload.description,
                severity=payload.severity,
                status="open",
                created_by=principal.user_id,
                assigned_to=payload.assignee_id,
            )
            await self.repository.insert(incident)
            self.repository.add_creation_details(
                IncidentTimelineEntry(
                    incident_id=incident.id,
                    actor_id=principal.user_id,
                    event_type="incident_created",
                    message="Incident created",
                ),
                [self._issue_link(incident.id, issue) for issue in snapshots],
            )
        return CreatedIncident.model_validate(incident)
