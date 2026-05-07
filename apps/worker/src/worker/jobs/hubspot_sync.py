"""DAI-031: HubSpot CRM sync job — pulls contacts from HubSpot into DealFlow leads."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
import sqlalchemy as sa

from worker.settings import get_settings
from worker.utils.crypto import decrypt

JOB_NAME = "hubspot_sync_job"

HUBSPOT_CONTACTS_URL = "https://api.hubapi.com/crm/v3/objects/contacts"
HUBSPOT_CONTACT_PROPERTIES = [
    "firstname",
    "lastname",
    "email",
    "phone",
    "hs_lead_status",
    "budget",
    "city",
    "state",
    "lifecyclestage",
]
PAGE_SIZE = 100

# ── SQL helpers ───────────────────────────────────────────────────────────────

_LOAD_CONNECTION_SQL = sa.text(
    """
    SELECT id, tenant_id, credentials_enc, last_sync_at, config
    FROM integration_connections
    WHERE id = :connection_id
      AND tenant_id = :tenant_id
      AND provider = 'hubspot'
      AND status = 'connected'
    """
)

_FIND_CONTACT_SQL = sa.text(
    """
    SELECT c.id
    FROM contacts c
    JOIN contact_points cp ON cp.contact_id = c.id
    WHERE c.tenant_id = :tenant_id
      AND cp.type = 'email'
      AND cp.value_normalized = :email_lower
    LIMIT 1
    """
)

_INSERT_CONTACT_SQL = sa.text(
    """
    INSERT INTO contacts (id, tenant_id, first_name, last_name, full_name, created_at, updated_at)
    VALUES (:id, :tenant_id, :first_name, :last_name, :full_name, :now, :now)
    RETURNING id
    """
)

_INSERT_CONTACT_POINT_SQL = sa.text(
    """
    INSERT INTO contact_points
        (id, contact_id, tenant_id, type, value_raw, value_normalized, is_primary, created_at)
    VALUES (:id, :contact_id, :tenant_id, :type, :value_raw, :value_normalized, true, :now)
    ON CONFLICT DO NOTHING
    """
)

_FIND_LEAD_BY_CRM_SQL = sa.text(
    """
    SELECT l.id FROM leads l
    JOIN sync_logs sl ON sl.lead_id = l.id
    WHERE sl.connection_id = :connection_id
      AND sl.crm_record_id = :crm_record_id
      AND sl.operation = 'hubspot.contact.upsert'
    LIMIT 1
    """
)

_INSERT_LEAD_SQL = sa.text(
    """
    INSERT INTO leads
        (id, tenant_id, contact_id, source_id, status, lead_type, raw_payload, created_at, updated_at)
    VALUES
        (:id, :tenant_id, :contact_id, :source_id, 'new', :lead_type, :raw_payload::jsonb, :now, :now)
    RETURNING id
    """
)

_FIND_HUBSPOT_SOURCE_SQL = sa.text(
    """
    SELECT id FROM lead_sources
    WHERE tenant_id = :tenant_id AND type = 'crm' AND source_key LIKE 'hubspot%'
    LIMIT 1
    """
)

_INSERT_SYNC_LOG_SQL = sa.text(
    """
    INSERT INTO sync_logs
        (id, tenant_id, connection_id, lead_id, idempotency_key, operation,
         status, crm_record_id, request_ref, response_ref, created_at)
    VALUES
        (:id, :tenant_id, :connection_id, :lead_id, :idempotency_key, :operation,
         :status, :crm_record_id, :request_ref::jsonb, :response_ref::jsonb, :now)
    ON CONFLICT (connection_id, idempotency_key) DO NOTHING
    """
)

_INSERT_TIMELINE_SQL = sa.text(
    """
    INSERT INTO activity_timeline
        (id, tenant_id, lead_id, event_type, event_data, actor_type, visible_to_agent, occurred_at, created_at)
    VALUES (:id, :tenant_id, :lead_id, 'lead.created', :event_data::jsonb, 'system', true, :now, :now)
    """
)

_UPDATE_CONNECTION_SQL = sa.text(
    """
    UPDATE integration_connections
    SET last_sync_at = :now, last_error_msg = NULL, updated_at = :now
    WHERE id = :connection_id
    """
)

_UPDATE_CONNECTION_ERROR_SQL = sa.text(
    """
    UPDATE integration_connections
    SET last_error_at = :now, last_error_msg = :msg, updated_at = :now
    WHERE id = :connection_id
    """
)


# ── HubSpot API client ────────────────────────────────────────────────────────


def _fetch_contacts_page(
    access_token: str,
    after: str | None,
    updated_after: datetime | None,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "limit": PAGE_SIZE,
        "properties": ",".join(HUBSPOT_CONTACT_PROPERTIES),
        "archived": "false",
    }
    if after:
        params["after"] = after
    if updated_after:
        # HubSpot filter: contacts updated since last sync
        params["filterGroups"] = json.dumps([{
            "filters": [{
                "propertyName": "lastmodifieddate",
                "operator": "GTE",
                "value": str(int(updated_after.timestamp() * 1000)),
            }]
        }])
    resp = httpx.post(
        f"{HUBSPOT_CONTACTS_URL}/search",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "filterGroups": [{
                "filters": [{
                    "propertyName": "lastmodifieddate",
                    "operator": "GTE",
                    "value": str(int((updated_after or datetime.min.replace(tzinfo=UTC)).timestamp() * 1000)),
                }]
            }],
            "properties": HUBSPOT_CONTACT_PROPERTIES,
            "limit": PAGE_SIZE,
            **({"after": after} if after else {}),
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()  # type: ignore[no-any-return]


def _map_lead_type(props: dict[str, Any]) -> str:
    stage = (props.get("lifecyclestage") or "").lower()
    mapping = {
        "subscriber": "unknown",
        "lead": "buyer",
        "marketingqualifiedlead": "buyer",
        "salesqualifiedlead": "buyer",
        "opportunity": "buyer",
        "customer": "buyer",
        "evangelist": "unknown",
        "other": "unknown",
    }
    return mapping.get(stage, "unknown")


# ── upsert helpers ────────────────────────────────────────────────────────────


async def _upsert_contact(
    session: Any,
    *,
    tenant_id: uuid.UUID,
    props: dict[str, Any],
    now: datetime,
) -> uuid.UUID:
    email: str | None = props.get("email") or None
    phone: str | None = props.get("phone") or None
    first_name: str | None = props.get("firstname") or None
    last_name: str | None = props.get("lastname") or None
    full_name = " ".join(p for p in (first_name, last_name) if p) or None

    if email:
        row = (
            await session.execute(_FIND_CONTACT_SQL, {"tenant_id": tenant_id, "email_lower": email.lower()})
        ).mappings().one_or_none()
        if row:
            return uuid.UUID(str(row["id"]))

    contact_id = uuid.uuid4()
    await session.execute(
        _INSERT_CONTACT_SQL,
        {
            "id": contact_id,
            "tenant_id": tenant_id,
            "first_name": first_name,
            "last_name": last_name,
            "full_name": full_name,
            "now": now,
        },
    )
    for cp_type, value in [("email", email), ("phone", phone)]:
        if value:
            await session.execute(
                _INSERT_CONTACT_POINT_SQL,
                {
                    "id": uuid.uuid4(),
                    "contact_id": contact_id,
                    "tenant_id": tenant_id,
                    "type": cp_type,
                    "value_raw": value,
                    "value_normalized": value.lower() if cp_type == "email" else value,
                    "now": now,
                },
            )
    return contact_id


async def _upsert_lead(
    session: Any,
    *,
    connection_id: uuid.UUID,
    tenant_id: uuid.UUID,
    source_id: uuid.UUID,
    contact_id: uuid.UUID,
    crm_record_id: str,
    props: dict[str, Any],
    now: datetime,
) -> tuple[uuid.UUID, bool]:
    """Return (lead_id, created)."""
    row = (
        await session.execute(
            _FIND_LEAD_BY_CRM_SQL,
            {"connection_id": connection_id, "crm_record_id": crm_record_id},
        )
    ).mappings().one_or_none()

    if row:
        return uuid.UUID(str(row["id"])), False

    lead_id = uuid.uuid4()
    await session.execute(
        _INSERT_LEAD_SQL,
        {
            "id": lead_id,
            "tenant_id": tenant_id,
            "contact_id": contact_id,
            "source_id": source_id,
            "lead_type": _map_lead_type(props),
            "raw_payload": json.dumps(props),
            "now": now,
        },
    )
    await session.execute(
        _INSERT_TIMELINE_SQL,
        {
            "id": uuid.uuid4(),
            "tenant_id": tenant_id,
            "lead_id": lead_id,
            "event_data": json.dumps({"source": "hubspot", "crm_id": crm_record_id}),
            "now": now,
        },
    )
    return lead_id, True


# ── main job ──────────────────────────────────────────────────────────────────


async def hubspot_sync_job(
    ctx: dict[str, Any],
    *,
    connection_id: str,
    tenant_id: str,
) -> dict[str, Any]:
    """ARQ job: sync HubSpot contacts into DealFlow leads for one tenant connection."""
    settings = get_settings()
    session_maker = ctx["session_maker"]
    cid = uuid.UUID(connection_id)
    tid = uuid.UUID(tenant_id)

    async with session_maker() as session:
        conn_row = (
            await session.execute(_LOAD_CONNECTION_SQL, {"connection_id": cid, "tenant_id": tid})
        ).mappings().one_or_none()

        if conn_row is None:
            return {"status": "skipped", "reason": "connection_not_found"}

        try:
            creds = json.loads(decrypt(conn_row["credentials_enc"], settings.secret_key or ""))
        except Exception:
            return {"status": "error", "reason": "credentials_decryption_failed"}

        access_token: str = creds.get("access_token", "")
        if not access_token:
            return {"status": "error", "reason": "no_access_token"}

        source_row = (
            await session.execute(_FIND_HUBSPOT_SOURCE_SQL, {"tenant_id": tid})
        ).mappings().one_or_none()
        if source_row is None:
            return {"status": "error", "reason": "no_hubspot_lead_source"}

        source_id = uuid.UUID(str(source_row["id"]))
        last_sync_at: datetime | None = conn_row["last_sync_at"]

        created = 0
        skipped = 0
        after: str | None = None
        now = datetime.now(tz=UTC)

        try:
            while True:
                page = _fetch_contacts_page(access_token, after, last_sync_at)
                contacts: list[dict[str, Any]] = page.get("results", [])

                for hs_contact in contacts:
                    crm_record_id = str(hs_contact["id"])
                    props: dict[str, Any] = hs_contact.get("properties", {})
                    idempotency_key = f"hs-contact-{crm_record_id}"

                    contact_id = await _upsert_contact(
                        session, tenant_id=tid, props=props, now=now
                    )
                    lead_id, was_created = await _upsert_lead(
                        session,
                        connection_id=cid,
                        tenant_id=tid,
                        source_id=source_id,
                        contact_id=contact_id,
                        crm_record_id=crm_record_id,
                        props=props,
                        now=now,
                    )

                    await session.execute(
                        _INSERT_SYNC_LOG_SQL,
                        {
                            "id": uuid.uuid4(),
                            "tenant_id": tid,
                            "connection_id": cid,
                            "lead_id": lead_id,
                            "idempotency_key": idempotency_key,
                            "operation": "hubspot.contact.upsert",
                            "status": "success",
                            "crm_record_id": crm_record_id,
                            "request_ref": json.dumps({"hs_id": crm_record_id}),
                            "response_ref": json.dumps({"lead_id": str(lead_id)}),
                            "now": now,
                        },
                    )

                    if was_created:
                        created += 1
                    else:
                        skipped += 1

                await session.flush()

                paging = page.get("paging", {})
                after = (paging.get("next") or {}).get("after")
                if not after:
                    break

        except httpx.HTTPError as exc:
            await session.rollback()
            async with session_maker() as err_session:
                await err_session.execute(
                    _UPDATE_CONNECTION_ERROR_SQL,
                    {"now": now, "msg": str(exc)[:500], "connection_id": cid},
                )
                await err_session.commit()
            return {"status": "error", "reason": str(exc)}

        await session.execute(_UPDATE_CONNECTION_SQL, {"now": now, "connection_id": cid})
        await session.commit()

    return {"status": "ok", "created": created, "skipped": skipped}
