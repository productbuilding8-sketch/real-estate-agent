"""TenantRepository — generic base that enforces tenant_id isolation on every query."""

from __future__ import annotations

import uuid
from typing import Any, Generic, TypeVar

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from dealflow.db.session import Base

T = TypeVar("T", bound=Base)


class TenantRepository(Generic[T]):
    """Base repository for any tenant-scoped model.

    All read and write operations automatically filter/stamp `tenant_id = self._tenant_id`.
    Callers must never pass tenant_id explicitly — this class owns that invariant.

    Usage::

        repo = TenantRepository(Lead, session, ctx.tenant_id)
        lead = await repo.get(lead_id)
        leads = await repo.list(Lead.status == "new", limit=20)
    """

    def __init__(
        self,
        model: type[T],
        session: AsyncSession,
        tenant_id: uuid.UUID,
    ) -> None:
        if not hasattr(model, "tenant_id"):
            raise TypeError(
                f"{model.__name__} has no tenant_id column — cannot use TenantRepository"
            )
        self._model = model
        self._session = session
        self._tenant_id = tenant_id

    # ── read ──────────────────────────────────────────────────────────────────

    async def get(self, id: uuid.UUID) -> T | None:
        """Fetch a single row by primary key, scoped to this tenant."""
        result = await self._session.execute(
            sa.select(self._model).where(
                self._model.id == id,  # type: ignore[attr-defined]
                self._model.tenant_id == self._tenant_id,  # type: ignore[attr-defined]
            )
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        *filters: Any,
        limit: int = 50,
        cursor: uuid.UUID | None = None,
    ) -> list[T]:
        """Return up to `limit` rows matching `filters`, ordered by id.

        `cursor` is the last `id` seen — pass it to fetch the next page (keyset pagination).
        """
        q = sa.select(self._model).where(
            self._model.tenant_id == self._tenant_id,  # type: ignore[attr-defined]
            *filters,
        )
        if cursor is not None:
            q = q.where(self._model.id > cursor)  # type: ignore[attr-defined]
        q = q.order_by(self._model.id).limit(limit)  # type: ignore[attr-defined]
        result = await self._session.execute(q)
        return list(result.scalars().all())

    async def exists(self, *filters: Any) -> bool:
        """Return True if any row matches filters within this tenant."""
        q = sa.select(
            sa.exists(
                sa.select(self._model.id).where(  # type: ignore[attr-defined]
                    self._model.tenant_id == self._tenant_id,  # type: ignore[attr-defined]
                    *filters,
                )
            )
        )
        result = await self._session.execute(q)
        return bool(result.scalar())

    # ── write ─────────────────────────────────────────────────────────────────

    async def add(self, obj: T) -> T:
        """Stamp tenant_id, persist, and refresh to load server defaults."""
        obj.tenant_id = self._tenant_id  # type: ignore[attr-defined]
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def delete(self, id: uuid.UUID) -> bool:
        """Delete by primary key. Returns True if a row was deleted."""
        result = await self._session.execute(
            sa.delete(self._model)
            .where(
                self._model.id == id,  # type: ignore[attr-defined]
                self._model.tenant_id == self._tenant_id,  # type: ignore[attr-defined]
            )
            .returning(self._model.id)  # type: ignore[attr-defined]
        )
        return result.scalar_one_or_none() is not None
