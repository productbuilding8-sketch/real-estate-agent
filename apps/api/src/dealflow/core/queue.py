"""ARQ job queue — lifespan-managed pool for enqueueing background jobs."""

from __future__ import annotations

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

_pool: ArqRedis | None = None

QUEUE_NAME = "dealflow:jobs"


async def init_job_queue(redis_url: str) -> None:
    global _pool
    _pool = await create_pool(RedisSettings.from_dsn(redis_url), default_queue_name=QUEUE_NAME)


async def close_job_queue() -> None:
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None


async def get_job_queue() -> ArqRedis | None:
    """FastAPI dependency — returns the shared ARQ pool, or None if not initialised."""
    return _pool
