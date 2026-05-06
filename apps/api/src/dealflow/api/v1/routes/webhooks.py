"""DAI-020: Inbound webhook endpoint for lead ingestion."""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from dealflow.core.queue import get_job_queue
from dealflow.db.session import get_session
from dealflow.services.webhooks import WebhookService

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class WebhookResponse(BaseModel):
    event_id: uuid.UUID
    status: str


@router.post(
    "/leads/{source_key}",
    response_model=WebhookResponse,
    summary="Ingest an inbound lead webhook",
    description=(
        "Receives a lead payload from an external source (e.g. HubSpot, web form). "
        "If the source has a `secret_hash` configured, the request must include an "
        "`X-Hub-Signature-256` header with a valid HMAC-SHA256 signature. "
        "Duplicate requests with the same `X-Idempotency-Key` are silently deduplicated."
    ),
)
async def ingest_lead_webhook(
    source_key: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    body: dict[str, Any],
    x_idempotency_key: Annotated[str | None, Header(alias="X-Idempotency-Key")] = None,
    x_hub_signature_256: Annotated[str | None, Header(alias="X-Hub-Signature-256")] = None,
    job_queue: Annotated[Any, Depends(get_job_queue)] = None,
) -> WebhookResponse:
    raw_body = json.dumps(body).encode()
    idempotency_key = x_idempotency_key or hashlib.sha256(raw_body).hexdigest()

    service = WebhookService(session)
    event = await service.ingest(
        source_key=source_key,
        payload=body,
        raw_body=raw_body,
        idempotency_key=idempotency_key,
        signature=x_hub_signature_256,
    )

    if event.lead_id is not None and job_queue is not None:
        await job_queue.enqueue_job(
            "score_lead_job",
            lead_id=str(event.lead_id),
            tenant_id=str(event.tenant_id),
        )

    return WebhookResponse(event_id=event.id, status=event.status)
