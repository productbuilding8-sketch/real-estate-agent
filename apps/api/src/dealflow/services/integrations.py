"""DAI-031: Integration management service — connect providers, trigger syncs."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from dealflow.core.crypto import encrypt
from dealflow.core.errors import AppError
from dealflow.db.models.integrations import IntegrationConnection

SUPPORTED_PROVIDERS = frozenset({"hubspot"})


class IntegrationService:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID, secret_key: str) -> None:
        self._session = session
        self._tenant_id = tenant_id
        self._secret_key = secret_key

    async def connect(
        self,
        *,
        provider: str,
        access_token: str,
        extra: dict[str, Any] | None = None,
    ) -> IntegrationConnection:
        """Store or update a provider connection for this tenant."""
        if provider not in SUPPORTED_PROVIDERS:
            raise AppError("unsupported_provider", f"Provider '{provider}' is not supported", 422)

        credentials = json.dumps({"access_token": access_token, **(extra or {})})
        credentials_enc = encrypt(credentials, self._secret_key)

        # Upsert: update existing connection if present
        existing = await self._load(provider)
        if existing is not None:
            existing.credentials_enc = credentials_enc
            existing.status = "connected"
            existing.last_error_msg = None
            await self._session.flush()
            return existing

        conn = IntegrationConnection(
            tenant_id=self._tenant_id,
            provider=provider,
            status="connected",
            credentials_enc=credentials_enc,
            config=extra,
        )
        self._session.add(conn)
        await self._session.flush()
        return conn

    async def disconnect(self, provider: str) -> None:
        conn = await self._load(provider)
        if conn is None:
            raise AppError("connection_not_found", f"No active connection for '{provider}'", 404)
        conn.status = "disconnected"
        conn.credentials_enc = None
        await self._session.flush()

    async def list_connections(self) -> list[IntegrationConnection]:
        result = await self._session.execute(
            sa.select(IntegrationConnection).where(
                IntegrationConnection.tenant_id == self._tenant_id,
            )
        )
        return list(result.scalars().all())

    async def get_connection(self, provider: str) -> IntegrationConnection | None:
        return await self._load(provider)

    async def _load(self, provider: str) -> IntegrationConnection | None:
        result = await self._session.execute(
            sa.select(IntegrationConnection).where(
                IntegrationConnection.tenant_id == self._tenant_id,
                IntegrationConnection.provider == provider,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    def to_safe_dict(conn: IntegrationConnection) -> dict[str, Any]:
        """Return connection data with credentials stripped."""
        return {
            "id": str(conn.id),
            "provider": conn.provider,
            "status": conn.status,
            "last_sync_at": conn.last_sync_at.isoformat()
            if isinstance(conn.last_sync_at, datetime)
            else None,
            "last_error_at": conn.last_error_at.isoformat()
            if isinstance(conn.last_error_at, datetime)
            else None,
            "last_error_msg": conn.last_error_msg,
            "created_at": conn.created_at.isoformat()
            if isinstance(conn.created_at, datetime)
            else None,
        }
