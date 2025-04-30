# tests/integration/conftest.py

import os
from unittest.mock import AsyncMock, MagicMock
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlmodel import SQLModel
from dotenv import load_dotenv

from marketplace_aggregator.adapters.marketplace import Marketplace
from marketplace_aggregator.repositories.listing_repo import ListingRepository
from marketplace_aggregator.repositories.promotional_rule_repo import PromotionalRuleRepository
from marketplace_aggregator.repositories.inventory_product_repo import InventoryProductRepository

# Load .env for TEST database URL
load_dotenv()

# Assume TEST_DATABASE_URL points to a different DB or port in .env
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://testuser:testpassword@localhost:5432/marketplace_test_db_test"
)

# Explicit metadata for test DB setup
test_metadata = SQLModel.metadata # Use the same metadata populated by models

@pytest_asyncio.fixture(scope="module")
async def test_engine():
    """Creates engine for the test database (module scope)."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture(scope="module")
async def setup_database(test_engine):
    """Creates all tables once per test module."""
    print("\nSetting up test database schema...")
    # Import all models needed to populate metadata
    from marketplace_aggregator.models import product, listing, variable_product, promotional_rule # noqa
    async with test_engine.begin() as conn:
        await conn.run_sync(test_metadata.drop_all) # Start clean
        await conn.run_sync(test_metadata.create_all)
    print("Test database schema created.")
    yield test_engine
    # Clean up after module
    async with test_engine.begin() as conn:
        await conn.run_sync(test_metadata.drop_all)
    print("Test database schema dropped.")

@pytest_asyncio.fixture(scope="module")
async def db_session_factory(setup_database):
    """Create a session factory for the test module."""
    return async_sessionmaker(
        setup_database,
        class_=AsyncSession,
        expire_on_commit=False
    )

@pytest_asyncio.fixture
async def db_session(db_session_factory):
    """Create a test database session with transaction isolation."""
    async with db_session_factory() as session:
        try:
            # Start a transaction
            await session.begin()
            yield session
            # Rollback the transaction
            await session.rollback()
        except Exception as e:
            await session.rollback()
            raise e

# --- Test Client Fixture ---
# This fixture also needs the event_loop if session-scoped
# @pytest_asyncio.fixture(scope="session")
# async def test_client(event_loop) -> AsyncGenerator[AsyncTestClient[Litestar], None]: # <-- Add event_loop
#     """Fixture to create an httpx test client for the Litestar app."""
#     # Import app inside fixture if needed to avoid top-level side effects
#     from marketplace_aggregator.main import app
#     app.debug = True # Ensure debug is set for testing context
#     async with AsyncTestClient(app=app) as client:
#         print("Test client created")
#         yield client
#     print("Test client closed")

@pytest.fixture(scope="function")
def mock_marketplace_adapter() -> MagicMock:
    mock_adapter = MagicMock(spec=Marketplace)
    mock_adapter.name = "TestPlace"
    mock_adapter.submit_listing = AsyncMock()
    mock_adapter.update_listing_price = AsyncMock()
    mock_adapter.update_listing_stock = AsyncMock()
    mock_adapter.get_orders = AsyncMock(return_value=[])
    return mock_adapter

# --- Fixtures providing REAL repositories using the test session ---
@pytest.fixture(scope="function")
def listing_repo(db_session: AsyncSession) -> ListingRepository:
     return ListingRepository(session=db_session)

@pytest.fixture(scope="function")
def rule_repo(db_session: AsyncSession) -> PromotionalRuleRepository:
     return PromotionalRuleRepository(session=db_session)

@pytest.fixture(scope="function")
def inventory_product_repo(db_session: AsyncSession) -> InventoryProductRepository:
     return InventoryProductRepository(session=db_session)

# ... fixtures for other real repositories ...

