from fastapi import APIRouter, Request, status
from pydantic import BaseModel
from sqlalchemy import text

from dealflow.config import get_settings
from dealflow.db.session import get_engine

router = APIRouter(tags=["system"])


class HealthResponse(BaseModel):
    status: str
    db: bool
    redis: bool


class VersionResponse(BaseModel):
    version: str
    environment: str
    app_name: str


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    status_code=status.HTTP_200_OK,
)
async def health_check() -> HealthResponse:
    db_ok = await _check_db()
    redis_ok = await _check_redis()
    return HealthResponse(status="ok", db=db_ok, redis=redis_ok)


@router.get(
    "/version",
    response_model=VersionResponse,
    summary="App version",
)
async def version(request: Request) -> VersionResponse:
    settings = request.app.state.settings
    return VersionResponse(
        version=settings.app_version,
        environment=settings.environment,
        app_name=settings.app_name,
    )


async def _check_db() -> bool:
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def _check_redis() -> bool:
    try:
        import redis.asyncio as aioredis

        settings = get_settings()
        client = aioredis.from_url(settings.redis_url, socket_connect_timeout=2)
        await client.ping()  # type: ignore[misc]
        await client.aclose()
        return True
    except Exception:
        return False
