import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from dealflow.config import Settings
from dealflow.db.session import Base, close_db, get_engine, init_db
from dealflow.main import create_app


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    return Settings(
        database_url="postgresql+asyncpg://dealflow:dealflow@localhost:5432/dealflow_test",
        redis_url="redis://localhost:6379/1",
        auth0_domain="test.auth0.com",
        auth0_audience="https://api.dealflow.test",
        secret_key="test-secret-key-for-tests-only",
        environment="test",
    )


@pytest.fixture
async def client(test_settings: Settings) -> AsyncClient:
    """Base client — no real DB required. Use db_session / db_client for tests
    that hit the database."""
    app = create_app(test_settings)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture(scope="session")
async def db_setup(test_settings: Settings):
    """Session-scoped — requires a running Postgres. Creates all tables once,
    drops them after the session. Only used by integration tests."""
    init_db(test_settings.database_url, testing=True)
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await close_db()


@pytest.fixture
async def db_session(test_settings: Settings, db_setup: None) -> AsyncSession:
    """Yields a real AsyncSession for integration tests that manipulate the DB directly."""
    factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest.fixture
async def db_client(test_settings: Settings, db_setup: None) -> AsyncClient:
    """HTTP client backed by real Postgres — for integration tests only."""
    app = create_app(test_settings)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
