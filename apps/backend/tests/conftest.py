import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Generator
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from httpx import ASGITransport

from src.app import app
from src.db import get_async_session, Base
from src.users import fastapi_users
from src.schemas import UserCreate

# Test database URL - using SQLite for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# Create async engine for testing
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=True,
    connect_args={"check_same_thread": False}
)

# Create session factory
TestingSessionLocal = sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest_asyncio.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create a test client with overridden database dependency."""

    def override_get_async_session():
        return db_session

    app.dependency_overrides[get_async_session] = override_get_async_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def test_user(db_session: AsyncSession) -> dict:
    """Create a test user and return authentication token."""
    user_data = {
        "email": "testuser@example.com",
        "password": "testpassword123",
        "is_active": True,
        "is_verified": True
    }

    # Create user using fastapi-users
    user = await fastapi_users.create_user(user_data)

    # Get auth token
    from src.users import auth_backend
    token_data = await auth_backend.strategy.generate_token(user)

    return {
        "user": user,
        "token": token_data,
        "headers": {"Authorization": f"Bearer {token_data}"}
    }


@pytest_asyncio.fixture(scope="function")
async def authenticated_client(client: AsyncClient, test_user: dict) -> AsyncGenerator[AsyncClient, None]:
    """Create an authenticated test client."""
    client.headers.update(test_user["headers"])
    yield client
    # Reset headers - Note: headers cannot be cleared after client is closed
    # This is handled by fixture scope management


@pytest.fixture
def sample_gold_price():
    """Sample gold price data for testing."""
    from datetime import datetime
    from src.schemas import GoldPriceCreate

    return GoldPriceCreate(
        symbol="spot",
        price=1250.75,
        usd_price=1985.50,
        timestamp=datetime.utcnow(),
        source="test"
    )


@pytest.fixture
def sample_gold96_price():
    """Sample gold 96 price data for testing."""
    from datetime import datetime
    from src.schemas import Gold96PriceCreate

    return Gold96PriceCreate(
        symbol="gold96",
        buy_price=1250.50,
        sell_price=1270.75,
        timestamp=datetime.utcnow(),
        source="test"
    )


@pytest.fixture
def sample_transaction_data():
    """Sample transaction data for testing."""
    return {
        "transaction_type": "buy",
        "quantity": 1.0,
        "price_per_unit": 1250.0,
        "total_amount": 1250.0
    }
