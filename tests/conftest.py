import asyncio
from collections.abc import AsyncGenerator
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.database import Base, get_db
from app.models.user import User
from app.models.enums import Role
from app.utils.security import _hash

TEST_DB_URL = "postgresql+asyncpg://test_user:test_pass@localhost/test_db"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DB_URL)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="session")
def TestAsyncSession(test_engine):
    return async_sessionmaker(test_engine, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def reset_db(test_engine):
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db(TestAsyncSession) -> AsyncGenerator[AsyncSession, None]:
    async with TestAsyncSession() as session:
        yield session


@pytest.fixture(autouse=True)
def override_db(TestAsyncSession):
    async def _override():
        async with TestAsyncSession() as session:
            yield session
    app.dependency_overrides[get_db] = _override
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


async def _make_authenticated_client(
    client: AsyncClient, db: AsyncSession, email: str, password: str, role: Role
) -> AsyncClient:
    user = User(
        name=role.value.replace("_", " ").title(),
        email=email,
        hashed_password=_hash(password),
        role=role,
        is_active=True,
    )
    db.add(user)
    await db.commit()

    res = await client.post("/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    client.headers["Authorization"] = f"Bearer {res.json()['access_token']}"
    return client


@pytest.fixture
async def admin_client(client, db):
    return await _make_authenticated_client(client, db, "admin@test.com", "Admin1234!", Role.admin)


@pytest.fixture
async def pm_client(client, db):
    return await _make_authenticated_client(client, db, "pm@test.com", "Manager1234!", Role.project_manager)


@pytest.fixture
async def member_client(client, db):
    return await _make_authenticated_client(client, db, "member@test.com", "Member1234!", Role.team_member)
