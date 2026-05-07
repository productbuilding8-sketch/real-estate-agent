"""ARQ WorkerSettings — entry point for the background worker process."""

from __future__ import annotations

from typing import Any

from arq.connections import RedisSettings

from worker.db import create_engine_and_session
from worker.jobs.score_lead import score_lead_job
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
    functions = [score_lead_job, send_sms_job]
    redis_settings = RedisSettings.from_dsn(_settings.redis_url)
    on_startup = on_startup
    on_shutdown = on_shutdown
    max_jobs = _settings.max_jobs
    job_timeout = _settings.job_timeout
    keep_result = 3600
    queue_name = "dealflow:jobs"
