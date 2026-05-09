"""DAI-039: Transactional outbox poller.

Runs every 15 seconds as an ARQ cron job. For each pending outbox_event it:
  1. Claims the row atomically (UPDATE WHERE status='pending' RETURNING).
  2. Enqueues the corresponding ARQ job via the worker's Redis connection.
  3. Marks the event processed, or retries with exponential back-off.
  4. After MAX_RETRIES failures the row is moved to 'dead' (dead-letter).

A recovery step at the start of each tick resets rows stuck in 'processing'
(e.g. from a worker crash) back to 'pending' after STALE_MINUTES.

Payload convention — the outbox event `payload` must contain exactly the
keyword arguments required by the target ARQ job function, e.g.:
  event_type='lead.sms.requested'  payload={'lead_id':..., 'tenant_id':..., 'message':...}
  event_type='lead.email.requested' payload={'lead_id':..., 'tenant_id':..., 'subject':..., 'body':...}
  event_type='lead.score.requested' payload={'lead_id':..., 'tenant_id':...}
  event_type='integration.hubspot.sync' payload={'connection_id':..., 'tenant_id':...}
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import sqlalchemy as sa

# ── Configuration ─────────────────────────────────────────────────────────────

MAX_RETRIES = 5
BATCH_SIZE = 50
STALE_MINUTES = 10  # 'processing' rows older than this are recovered

# Exponential back-off delays per attempt (seconds): 30s, 2m, 8m, 30m, 2h
_BACKOFF = [30, 120, 480, 1800, 7200]

# event_type → ARQ job function name (must match a function in WorkerSettings.functions)
_DISPATCH: dict[str, str] = {
    "lead.sms.requested": "send_sms_job",
    "lead.email.requested": "send_email_job",
    "lead.score.requested": "llm_score_lead_job",
    "integration.hubspot.sync": "hubspot_sync_job",
}

_QUEUE = "dealflow:jobs"

# ── SQL ───────────────────────────────────────────────────────────────────────

# Reset rows stuck in 'processing' after a worker crash.
_RECOVER_STALE_SQL = sa.text("""
    UPDATE outbox_events
    SET status = 'pending',
        next_attempt_at = :now
    WHERE status = 'processing'
      AND last_attempt_at < :threshold
""")

# Read pending candidates without acquiring a lock (no contention on reads).
_LIST_PENDING_SQL = sa.text("""
    SELECT id, event_type, payload, attempts
    FROM outbox_events
    WHERE status = 'pending'
      AND (next_attempt_at IS NULL OR next_attempt_at <= :now)
    ORDER BY created_at
    LIMIT :batch
""")

# Claim one row atomically — concurrent workers that also read the same row
# will get 0 rows back from RETURNING and skip it.
_CLAIM_SQL = sa.text("""
    UPDATE outbox_events
    SET status          = 'processing',
        last_attempt_at = :now,
        attempts        = attempts + 1
    WHERE id     = :id
      AND status = 'pending'
    RETURNING attempts
""")

_MARK_DONE_SQL = sa.text("""
    UPDATE outbox_events
    SET status       = 'processed',
        processed_at = :now,
        error        = NULL
    WHERE id = :id
""")

# Back-off retry: return to 'pending' with a future next_attempt_at.
_MARK_RETRY_SQL = sa.text("""
    UPDATE outbox_events
    SET status          = 'pending',
        error           = :error,
        next_attempt_at = :next_attempt_at
    WHERE id = :id
""")

# Dead-letter: exceeded MAX_RETRIES, will not be retried automatically.
_MARK_DEAD_SQL = sa.text("""
    UPDATE outbox_events
    SET status = 'dead',
        error  = :error
    WHERE id = :id
""")


# ── Job ───────────────────────────────────────────────────────────────────────


async def poll_outbox_job(ctx: dict[str, Any]) -> dict[str, Any]:
    """ARQ cron job: drain the outbox_events table one batch at a time."""
    session_maker = ctx["session_maker"]
    redis = ctx["redis"]
    now = datetime.now(tz=UTC)
    stale_threshold = now - timedelta(minutes=STALE_MINUTES)
    dispatched = 0
    retried = 0
    dead = 0

    # 1. Recover stale 'processing' rows from previous crashed ticks.
    async with session_maker() as session:
        await session.execute(_RECOVER_STALE_SQL, {"now": now, "threshold": stale_threshold})
        await session.commit()

    # 2. Read a batch of candidates (no lock — fast read).
    async with session_maker() as session:
        rows = (
            (await session.execute(_LIST_PENDING_SQL, {"now": now, "batch": BATCH_SIZE}))
            .mappings()
            .all()
        )

    # 3. Process each candidate.
    for row in rows:
        event_id: uuid.UUID = row["id"]
        event_type: str = row["event_type"]
        payload: dict[str, Any] = dict(row["payload"] or {})

        # Claim atomically — skip if another worker beat us to it.
        async with session_maker() as session:
            claimed = (
                (await session.execute(_CLAIM_SQL, {"id": event_id, "now": now}))
                .mappings()
                .one_or_none()
            )
            await session.commit()

        if claimed is None:
            continue

        attempts: int = claimed["attempts"]  # already incremented by CLAIM_SQL
        job_name = _DISPATCH.get(event_type)

        async with session_maker() as session:
            try:
                if job_name is None:
                    raise ValueError(f"No handler registered for event_type={event_type!r}")

                await redis.enqueue_job(job_name, _queue_name=_QUEUE, **payload)
                await session.execute(_MARK_DONE_SQL, {"id": event_id, "now": now})
                dispatched += 1

            except Exception as exc:
                error_msg = str(exc)[:500]

                if attempts >= MAX_RETRIES:
                    await session.execute(_MARK_DEAD_SQL, {"id": event_id, "error": error_msg})
                    dead += 1
                else:
                    delay = _BACKOFF[min(attempts - 1, len(_BACKOFF) - 1)]
                    next_attempt_at = now + timedelta(seconds=delay)
                    await session.execute(
                        _MARK_RETRY_SQL,
                        {
                            "id": event_id,
                            "error": error_msg,
                            "next_attempt_at": next_attempt_at,
                        },
                    )
                    retried += 1

            await session.commit()

    return {"status": "ok", "dispatched": dispatched, "retried": retried, "dead": dead}
