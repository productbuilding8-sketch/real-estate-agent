from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from dealflow.api.v1.router import api_router
from dealflow.config import Settings, get_settings
from dealflow.core.errors import register_error_handlers
from dealflow.core.queue import close_job_queue, init_job_queue
from dealflow.db.session import close_db, init_db

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    logger.info("startup", environment=settings.environment, version=settings.app_version)

    init_db(settings.database_url)
    logger.info("database_pool_ready")

    try:
        await init_job_queue(settings.redis_url)
        logger.info("job_queue_ready")
    except Exception:
        logger.warning("job_queue_unavailable")

    yield

    await close_job_queue()
    await close_db()
    logger.info("shutdown")


def create_app(settings: Settings | None = None) -> FastAPI:
    cfg = settings or get_settings()

    app = FastAPI(
        title=cfg.app_name,
        version=cfg.app_version,
        docs_url="/docs" if not cfg.is_production else None,
        redoc_url="/redoc" if not cfg.is_production else None,
        openapi_url="/openapi.json" if not cfg.is_production else None,
        lifespan=lifespan,
    )

    app.state.settings = cfg

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"] if not cfg.is_production else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_error_handlers(app)
    app.include_router(api_router)

    return app


app = create_app()
