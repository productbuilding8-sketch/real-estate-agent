"""DAI-031: Integration management endpoints (connect, list, trigger sync)."""

from __future__ import annotations

from typing import Annotated, Any

from arq.connections import ArqRedis
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from dealflow.api.v1.schemas.integrations import (
    ConnectionResponse,
    ConnectRequest,
    TriggerSyncResponse,
)
from dealflow.config import get_settings
from dealflow.core.dependencies import require_permission
from dealflow.core.errors import AppError
from dealflow.core.queue import get_job_queue
from dealflow.core.rbac import RequestContext
from dealflow.db.session import get_session
from dealflow.services.integrations import IntegrationService

router = APIRouter(prefix="/integrations", tags=["integrations"])


def _make_service(session: AsyncSession, ctx: RequestContext) -> IntegrationService:
    return IntegrationService(session, ctx.tenant_id, get_settings().secret_key)


@router.get(
    "",
    response_model=list[ConnectionResponse],
    summary="List all integration connections for this tenant",
)
async def list_integrations(
    ctx: Annotated[RequestContext, Depends(require_permission("integrations:read"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[ConnectionResponse]:
    service = _make_service(session, ctx)
    connections = await service.list_connections()
    return [
        ConnectionResponse(
            id=c.id,
            provider=c.provider,
            status=c.status,
            last_sync_at=c.last_sync_at,
            last_error_at=c.last_error_at,
            last_error_msg=c.last_error_msg,
            created_at=c.created_at,
        )
        for c in connections
    ]


@router.post(
    "/connect",
    response_model=ConnectionResponse,
    status_code=201,
    summary="Connect or update a CRM/integration provider",
)
async def connect_integration(
    body: ConnectRequest,
    ctx: Annotated[RequestContext, Depends(require_permission("integrations:write"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ConnectionResponse:
    service = _make_service(session, ctx)
    extra: dict[str, Any] = {}
    if body.portal_id:
        extra["portal_id"] = body.portal_id

    conn = await service.connect(
        provider=body.provider,
        access_token=body.access_token,
        extra=extra or None,
    )
    await session.commit()
    return ConnectionResponse(
        id=conn.id,
        provider=conn.provider,
        status=conn.status,
        last_sync_at=conn.last_sync_at,
        last_error_at=conn.last_error_at,
        last_error_msg=conn.last_error_msg,
        created_at=conn.created_at,
    )


@router.delete(
    "/{provider}",
    status_code=204,
    summary="Disconnect an integration provider",
)
async def disconnect_integration(
    provider: str,
    ctx: Annotated[RequestContext, Depends(require_permission("integrations:write"))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    service = _make_service(session, ctx)
    await service.disconnect(provider)
    await session.commit()


@router.post(
    "/{provider}/sync",
    response_model=TriggerSyncResponse,
    status_code=202,
    summary="Trigger a manual CRM sync for the given provider",
)
async def trigger_sync(
    provider: str,
    ctx: Annotated[RequestContext, Depends(require_permission("integrations:write"))],
    session: Annotated[AsyncSession, Depends(get_session)],
    queue: Annotated[ArqRedis | None, Depends(get_job_queue)] = None,
) -> TriggerSyncResponse:
    service = _make_service(session, ctx)
    conn = await service.get_connection(provider)

    if conn is None or conn.status != "connected":
        raise AppError("connection_not_found", f"No active '{provider}' connection", 404)

    if queue is None:
        return TriggerSyncResponse(queued=False, reason="queue_unavailable")

    job_fn = f"{provider}_sync_job"
    job = await queue.enqueue_job(
        job_fn,
        connection_id=str(conn.id),
        tenant_id=str(ctx.tenant_id),
    )
    return TriggerSyncResponse(queued=True, job_id=job.job_id if job else None)
