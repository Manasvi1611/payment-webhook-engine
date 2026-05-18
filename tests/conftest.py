import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def test_engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def override_db(test_engine):
    """Override the FastAPI DB dependency to use the in-memory SQLite engine."""
    SessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)

    async def _get_test_db():
        async with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = _get_test_db
    yield SessionLocal
    app.dependency_overrides.clear()


@pytest.fixture
async def client(override_db):
    """AsyncClient wired to the FastAPI app with the test DB."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
