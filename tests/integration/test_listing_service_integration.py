# tests/integration/test_listing_service_integration.py

import pytest
from unittest.mock import MagicMock, AsyncMock
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Import REAL repositories and service, models, etc.
from marketplace_aggregator.repositories.inventory_product_repo import InventoryProductRepository
from marketplace_aggregator.services.listing_service import ListingService
from marketplace_aggregator.repositories.listing_repo import ListingRepository
from marketplace_aggregator.repositories.promotional_rule_repo import PromotionalRuleRepository
# ... import other real product repos ...
# from marketplace_aggregator.adapters.marketplace import Marketplace
from marketplace_aggregator.models.promotional_rule import PromotionalRule, ProductTypeEnum
from marketplace_aggregator.models.product import InventoryProduct
# from marketplace_aggregator.models.listing import Listing

# Use pytest-asyncio marker with module scope for integration tests
# pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest.mark.asyncio(loop_scope="module")
async def test_db_session_is_active(db_session: AsyncSession):
    assert db_session is not None
    assert db_session.is_active

@pytest.mark.asyncio(loop_scope="module")
async def test_tables_are_created(db_session: AsyncSession):
    """
    Test that the tables are created in the test database.
    """
    # get all tables in the test database, use the Postgres dialect
    result = await db_session.scalars(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'"))
    tables = [row for row in result]
    print(tables)
    # check if the tables are created
    assert tables is not None
    # check if the assembly, inventoryproduct, listing, promotionalrule, serviceproduct, variableproduct tables are created
    assert "assembly" in tables
    assert "inventoryproduct" in tables
    assert "listing" in tables
    assert "promotionalrule" in tables
    assert "serviceproduct" in tables
    assert "variableproduct" in tables
    assert db_session is not None
    assert db_session.is_active


@pytest.mark.asyncio(loop_scope="module")
async def test_list_item_integration_success(
    db_session: AsyncSession,
    rule_repo: PromotionalRuleRepository,
    listing_repo: ListingRepository,
    inventory_product_repo: InventoryProductRepository,
    mock_marketplace_adapter: MagicMock
):
    """
    Integration test: Verify listing creation persists data correctly.
    """
    # Arrange: Create prerequisite data IN THE TEST DATABASE
    # 1. Create Product
    test_product = InventoryProduct(sku="INT-TEST-01", title="Integration Test Prod", price=50.0)
    await inventory_product_repo.add(test_product) # Use real repo

    # 2. Create Rule
    test_rule = PromotionalRule(
        product_identifier=test_product.sku,
        marketplace_name=mock_marketplace_adapter.name,
        product_type=ProductTypeEnum.INVENTORY.value,
        is_active=True
    )
    saved_rule = await rule_repo.add(test_rule)
    await db_session.commit()
    rule_id = saved_rule.id
    assert rule_id is not None

    # 3. Configure Mock Adapter for success
    expected_listing_id = f"MOCK-INT-{rule_id}"
    mock_marketplace_adapter.submit_listing = AsyncMock(return_value=expected_listing_id)

    # 4. Create Service instance with REAL repos and MOCK adapter
    adapters = {mock_marketplace_adapter.name: mock_marketplace_adapter}
    service = ListingService(
        promotional_rule_repo=rule_repo,
        inventory_product_repo=inventory_product_repo,
        variable_product_repo=MagicMock(),
        assembly_repo=MagicMock(),
        service_product_repo=MagicMock(),
        listing_repo=listing_repo,
        marketplace_adapters=adapters,
        db_session=db_session
    )

    # Act: Call the service method
    # Transaction managed by session.begin_nested in fixture (will rollback after test)
    # OR wrap service call in session.begin() if fixture doesn't handle it
    result_listing_id = await service.list_item_on_marketplace(rule_id=rule_id)

    # Assert
    # 1. Check return value
    assert result_listing_id == expected_listing_id

    # 2. Verify data in DB: Fetch the listing record using the repo
    #    Need to potentially flush the session if commit isn't forced yet
    await db_session.flush() # Ensure data added by service is queryable
    created_listing = await listing_repo.get_by_composite_id(
        mock_marketplace_adapter.name,
        expected_listing_id
    )
    assert created_listing is not None
    assert created_listing.rule_id == rule_id
    assert created_listing.product_identifier == test_product.sku
    assert created_listing.status == "pending"

    # 3. Verify adapter was called (optional, but good)
    mock_marketplace_adapter.submit_listing.assert_awaited_once()