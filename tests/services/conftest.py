# tests/services/conftest.py

import pytest
from unittest.mock import MagicMock, AsyncMock

# Import interfaces/classes needed for fixtures
from marketplace_aggregator.services.listing_service import ListingService
from marketplace_aggregator.repositories.promotional_rule_repo import (
    PromotionalRuleRepository,
)
from marketplace_aggregator.repositories.inventory_product_repo import (
    InventoryProductRepository,
)
from marketplace_aggregator.repositories.variable_product_repo import (
    VariableProductRepository,
)
from marketplace_aggregator.repositories.assembly_repo import AssemblyRepository
from marketplace_aggregator.repositories.service_product_repo import (
    ServiceProductRepository,
)
from marketplace_aggregator.repositories.listing_repo import ListingRepository
from marketplace_aggregator.adapters.marketplace import Marketplace
from sqlalchemy.ext.asyncio import AsyncSession

# --- Move ALL Fixtures Here ---


@pytest.fixture
def mock_promotional_rule_repo() -> MagicMock:
    mock = MagicMock(spec=PromotionalRuleRepository)
    mock.get = AsyncMock()
    mock.find_active_rule_for_marketplace = AsyncMock()
    return mock


@pytest.fixture
def mock_inventory_product_repo() -> MagicMock:
    mock = MagicMock(spec=InventoryProductRepository)
    mock.get_by_sku = AsyncMock()
    return mock


@pytest.fixture
def mock_variable_product_repo() -> MagicMock:
    mock = MagicMock(spec=VariableProductRepository)
    mock.get_by_group_id = AsyncMock()
    return mock


@pytest.fixture
def mock_assembly_repo() -> MagicMock:
    mock = MagicMock(spec=AssemblyRepository)
    mock.get_by_sku = AsyncMock()
    return mock


@pytest.fixture
def mock_service_product_repo() -> MagicMock:
    mock = MagicMock(spec=ServiceProductRepository)
    mock.get_by_sku = AsyncMock()
    return mock


@pytest.fixture
def mock_listing_repo() -> MagicMock:
    mock = MagicMock(spec=ListingRepository)
    mock.add = AsyncMock(return_value=None)
    mock.update = AsyncMock(return_value=None)
    mock.get_by_composite_id = AsyncMock()
    return mock


@pytest.fixture
def mock_marketplace_adapter() -> MagicMock:
    mock_adapter = MagicMock(spec=Marketplace)
    mock_adapter.name = "TestPlace"
    mock_adapter.submit_listing = AsyncMock()
    mock_adapter.update_listing_price = AsyncMock()
    mock_adapter.update_listing_stock = AsyncMock()
    mock_adapter.get_orders = AsyncMock(return_value=[])
    return mock_adapter


@pytest.fixture
def mock_db_session() -> MagicMock:
    """Creates a mock database session suitable for 'async with session.begin():'."""
    mock_session = MagicMock(spec=AsyncSession)

    # Mock the transaction context manager returned by begin()
    mock_transaction = AsyncMock() # The object returned by begin()
    # Configure its __aenter__ and __aexit__ methods
    # __aenter__ usually returns the transaction object itself or None
    mock_transaction.__aenter__.return_value = None
    # __aexit__ needs to accept exception type, value, traceback args
    # Configure it to return None (indicating success/exception handled)
    mock_transaction.__aexit__ = AsyncMock(return_value=None)

    # Configure the session's begin() method to return our mock transaction
    mock_session.begin = MagicMock(return_value=mock_transaction)

    # Mock other methods if the service calls them directly (optional)
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.flush = AsyncMock()
    # Add mock implementations for add, scalar, scalars etc. if service uses them directly

    return mock_session


@pytest.fixture
def listing_service(
    mock_promotional_rule_repo,
    mock_inventory_product_repo,
    mock_variable_product_repo,
    mock_assembly_repo,
    mock_service_product_repo,
    mock_listing_repo,
    mock_marketplace_adapter,
    mock_db_session,
) -> ListingService:
    """Creates a ListingService instance with all mocked dependencies."""
    adapters = {mock_marketplace_adapter.name: mock_marketplace_adapter}
    service = ListingService(
        promotional_rule_repo=mock_promotional_rule_repo,
        inventory_product_repo=mock_inventory_product_repo,
        variable_product_repo=mock_variable_product_repo,
        assembly_repo=mock_assembly_repo,
        service_product_repo=mock_service_product_repo,
        listing_repo=mock_listing_repo,
        marketplace_adapters=adapters,
        db_session=mock_db_session,
    )
    return service
