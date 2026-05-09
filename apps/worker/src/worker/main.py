"""ARQ WorkerSettings — entry point for the background worker process."""

from __future__ import annotations

from typing import Any

from arq import cron
from arq.connections import RedisSettings

from worker.db import create_engine_and_session
from worker.jobs.hubspot_sync import hubspot_sync_job
from worker.jobs.llm_score_lead import llm_score_lead_job
from worker.jobs.poll_outbox import poll_outbox_job
from worker.jobs.score_lead import score_lead_job
from worker.jobs.send_email import send_email_job
from worker.jobs.send_sms import send_sms_job
from worker.settings import get_settings

_settings = get_settings()


async def on_startup(ctx: dict[str, Any]) -> None:
    engine, session_maker = create_engine_and_session(_settings.database_url)
    ctx["engine"] = engine
    ctx["session_maker"] = session_maker


async def on_shutdown(ctx: dict[str, Any]) -> None:
    engine = ctx.get("engine")
    if engine is not None:
        await engine.dispose()


class WorkerSettings:
    functions = [score_lead_job, send_sms_job, send_email_job, llm_score_lead_job, hubspot_sync_job]
    cron_jobs = [
        # Drain the transactional outbox every 15 seconds.
        cron(poll_outbox_job, second={0, 15, 30, 45}, run_at_startup=True),
    ]
    redis_settings = RedisSettings.from_dsn(_settings.redis_url)
    on_startup = on_startup
    on_shutdown = on_shutdown
    max_jobs = _settings.max_jobs
    job_timeout = _settings.job_timeout
    keep_result = 3600
    queue_name = "dealflow:jobs"
