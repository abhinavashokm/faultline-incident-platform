from uuid import UUID

from fastapi import APIRouter, Depends, status
from faultline_auth import Principal, get_principal
from sqlalchemy.ext.asyncio import AsyncSession

from app.alerts.schemas import (
    AlertResponse,
    AlertRuleCreate,
    AlertRuleResponse,
    AlertRuleUpdate,
)
from app.alerts.service import AlertRuleService
from app.core.db import get_session

router = APIRouter(tags=["alerts"])


@router.get(
    "/projects/{project_id}/alert-rules",
    response_model=list[AlertRuleResponse],
    summary="List alert rules",
)
async def list_alert_rules(
    project_id: UUID,
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_session),
) -> list[AlertRuleResponse]:
    """List configured alert rules for a project."""
    service = AlertRuleService(session)
    return await service.list_rules(project_id)


@router.post(
    "/projects/{project_id}/alert-rules",
    response_model=AlertRuleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create alert rule",
)
async def create_alert_rule(
    project_id: UUID,
    rule_in: AlertRuleCreate,
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_session),
) -> AlertRuleResponse:
    """Create a new alert rule."""
    service = AlertRuleService(session)
    return await service.create_rule(
        project_id=project_id,
        rule_in=rule_in,
        created_by=principal.user_id if principal else None,
    )


@router.patch(
    "/projects/{project_id}/alert-rules/{rule_id}",
    response_model=AlertRuleResponse,
    summary="Update alert rule",
)
async def update_alert_rule(
    project_id: UUID,
    rule_id: UUID,
    rule_in: AlertRuleUpdate,
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_session),
) -> AlertRuleResponse:
    """Update an existing alert rule."""
    service = AlertRuleService(session)
    return await service.update_rule(
        project_id=project_id,
        rule_id=rule_id,
        rule_in=rule_in,
    )


@router.delete(
    "/projects/{project_id}/alert-rules/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete alert rule",
)
async def delete_alert_rule(
    project_id: UUID,
    rule_id: UUID,
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete an alert rule."""
    service = AlertRuleService(session)
    await service.delete_rule(project_id=project_id, rule_id=rule_id)


@router.get(
    "/projects/{project_id}/alerts",
    response_model=list[AlertResponse],
    summary="List alerts",
)
async def list_alerts(
    project_id: UUID,
    principal: Principal = Depends(get_principal),
) -> list[AlertResponse]:
    """List triggered alerts for a project."""
    return []


@router.get(
    "/projects/{project_id}/alerts/{alert_id}",
    response_model=AlertResponse,
    summary="Get alert detail",
)
async def get_alert(
    project_id: UUID,
    alert_id: UUID,
    principal: Principal = Depends(get_principal),
) -> AlertResponse:
    """Fetch details for a specific alert."""
    raise NotImplementedError("Alert detail will be wired in the service implementation")
