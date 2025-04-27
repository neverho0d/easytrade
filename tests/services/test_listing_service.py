# tests/services/test_listing_service.py

import pytest
from unittest.mock import (
    ANY,
    AsyncMock,
    MagicMock,
)  # Can use MagicMock directly or pytest-mock fixture

# Import the code to be tested and the interfaces to be mocked
from marketplace_aggregator.models.listing import Listing
from marketplace_aggregator.models.promotional_rule import (
    ProductTypeEnum,
    PromotionalRule,
)
from marketplace_aggregator.repositories.assembly_repo import AssemblyRepository
from marketplace_aggregator.repositories.inventory_product_repo import (
    InventoryProductRepository,
)
from marketplace_aggregator.repositories.listing_repo import ListingRepository
from marketplace_aggregator.repositories.promotional_rule_repo import (
    PromotionalRuleRepository,
)
from marketplace_aggregator.repositories.service_product_repo import (
    ServiceProductRepository,
)
from marketplace_aggregator.repositories.variable_product_repo import (
    VariableProductRepository,
)
from marketplace_aggregator.services.listing_service import ListingService
from marketplace_aggregator.adapters.marketplace import Marketplace, ListingError
from marketplace_aggregator.models.product import InventoryProduct  # For test data


# --- Pytest Fixtures for Setup ---
@pytest.fixture
def mock_inventory_product_repo() -> MagicMock:
    return MagicMock(spec=InventoryProductRepository)


@pytest.fixture
def mock_service_product_repo() -> MagicMock:
    return MagicMock(spec=ServiceProductRepository)


@pytest.fixture
def mock_assembly_repo() -> MagicMock:
    return MagicMock(spec=AssemblyRepository)


@pytest.fixture
def mock_variable_product_repo() -> MagicMock:
    return MagicMock(spec=VariableProductRepository)


@pytest.fixture
def mock_promotional_rule_repo() -> MagicMock:
    # Use AsyncMock if methods are directly awaited in test setup,
    # but MagicMock with spec often works if just configuring return values/side_effects
    return MagicMock(spec=PromotionalRuleRepository)


@pytest.fixture
def mock_listing_repo() -> MagicMock:
    """Creates a mock ListingRepository."""
    mock_repo = MagicMock(spec=ListingRepository)
    mock_repo.add = AsyncMock(return_value=None)
    return mock_repo


@pytest.fixture
def mock_marketplace_adapter() -> MagicMock:
    """Creates a mock Marketplace adapter."""
    mock_adapter = MagicMock(spec=Marketplace)
    # Set the 'name' property required by the interface
    mock_adapter.name = "TestPlace"
    return mock_adapter


@pytest.fixture
def listing_service(
    mock_promotional_rule_repo,
    mock_inventory_product_repo,
    mock_variable_product_repo,
    mock_assembly_repo,
    mock_service_product_repo,
    mock_listing_repo,
    mock_marketplace_adapter,
) -> ListingService:
    """Creates a ListingService instance with mocked dependencies."""
    # Create the dictionary of adapters to inject
    adapters = {mock_marketplace_adapter.name: mock_marketplace_adapter}
    # Inject the mocks into the service instance
    service = ListingService(
        promotional_rule_repo=mock_promotional_rule_repo,
        inventory_product_repo=mock_inventory_product_repo,
        variable_product_repo=mock_variable_product_repo,
        assembly_repo=mock_assembly_repo,
        service_product_repo=mock_service_product_repo,
        listing_repo=mock_listing_repo,
        marketplace_adapters=adapters,
    )
    return service


# --- Test Cases ---


@pytest.mark.asyncio
async def test_list_item_success(
    listing_service: ListingService,
    mock_promotional_rule_repo: MagicMock,
    mock_listing_repo: MagicMock,
    mock_marketplace_adapter: MagicMock,
    mocker,  # Use pytest-mock's mocker fixture for patching
):
    """
    Test the successful path for listing an item.
    """
    # Arrange: Configure the mocks
    rule_id = 1
    test_sku = "TEST-SKU-01"
    marketplace_name = "TestPlace"
    expected_listing_id = "MOCK-LISTING-123"

    # Create a mock rule
    mock_rule = PromotionalRule(
        id=rule_id,
        product_identifier=test_sku,
        marketplace_name=marketplace_name,
        product_type=ProductTypeEnum.INVENTORY.value,
        is_active=True,
        marketplace_specific_settings={"setting": "value"},
    )
    # Create sample product data to be returned by the repo mock
    # Create an instance of InventoryProduct (or VariableProduct)
    #       Make sure it has a .sku or .group_id attribute matching test_sku
    mock_product = InventoryProduct(sku=test_sku, title="Test Item", price=10.0)
    # Mock listing created internally
    expected_listing = Listing(
        product_identifier=test_sku,
        rule_id=rule_id,
        marketplace_name=marketplace_name,
        marketplace_listing_id=expected_listing_id,
        status="active",
        listed_price=10.0,
    )

    # Configure Mocks
    mock_promotional_rule_repo.get = AsyncMock(
        return_value=mock_rule
    )  # Mock async method
    mock_marketplace_adapter.submit_listing = AsyncMock(
        return_value=expected_listing_id
    )  # Mock async method
    mock_listing_repo.add = AsyncMock(return_value=None)  # Mock async method

    # Mock the internal helper method to isolate list_item_on_marketplace logic
    mock_get_product_data_and_rule = mocker.patch.object(
        listing_service,
        "_get_product_data_and_rule",
        new_callable=AsyncMock,
        return_value=(mock_product, mock_rule),
    )

    # Act: Call the service method under test
    # Call listing_service.list_item_on_marketplace(...) and store the result
    actual_listing_id = await listing_service.list_item_on_marketplace(rule_id=rule_id)

    # Assert: Check the results and mock interactions
    assert actual_listing_id == expected_listing_id
    # Check awaited calls
    # mock_promotional_rule_repo.get.assert_awaited_once_with(rule_id)
    mock_get_product_data_and_rule.assert_awaited_once_with(rule_id)
    mock_marketplace_adapter.submit_listing.assert_awaited_once_with(
        mock_product, listing_config=mock_rule.marketplace_specific_settings
    )
    # Check the call to listing repo add - use ANY or check details
    mock_listing_repo.add.assert_awaited_once()
    # Get the object passed to the mock's call
    call_args, _ = mock_listing_repo.add.call_args
    actual_listing_obj = call_args[0]
    assert isinstance(actual_listing_obj, Listing)
    assert actual_listing_obj.rule_id == expected_listing.rule_id
    assert (
        actual_listing_obj.marketplace_listing_id
        == expected_listing.marketplace_listing_id
    )
    assert actual_listing_obj.status == expected_listing.status
    assert actual_listing_obj.listed_price == expected_listing.listed_price


# --- Test Case for Rule Not Found ---
@pytest.mark.asyncio
async def test_list_item_rule_not_found(
    listing_service: ListingService,
    mock_promotional_rule_repo: MagicMock,
    mock_marketplace_adapter: MagicMock,
):
    """
    Test listing when the rule is not found.
    """
    # Arrange: Configure the promotional rule repo mock to return None
    mock_promotional_rule_repo.get.return_value = None

    # Act: Call the service method
    actual_listing_id = await listing_service.list_item_on_marketplace(rule_id=1)

    # Assert: Check the outcome
    assert actual_listing_id is None
    # Check the marketplace adapter was *NOT* called
    mock_marketplace_adapter.submit_listing.assert_not_called()


# --- Test Case for Rule Not Active ---
@pytest.mark.asyncio
async def test_list_item_rule_not_active(
    listing_service: ListingService,
    mock_promotional_rule_repo: MagicMock,
    mock_listing_repo: MagicMock,
    mock_marketplace_adapter: MagicMock,
):
    """
    Test listing when the rule is not active.
    """
    # Arrange: Configure the promotional rule repo mock to return a non-active rule
    rule_id = 1
    test_sku = "TEST-SKU-01"
    marketplace_name = "TestPlace"
    mock_rule = PromotionalRule(
        id=rule_id,
        product_identifier=test_sku,
        marketplace_name=marketplace_name,
        product_type=ProductTypeEnum.INVENTORY.value,
        is_active=False,
        marketplace_specific_settings={"setting": "value"},
    )
    mock_promotional_rule_repo.get.return_value = mock_rule
    # Act: Call the service method
    actual_listing_id = await listing_service.list_item_on_marketplace(rule_id=rule_id)

    # Assert: Check the outcome
    assert actual_listing_id is None
    # Check the marketplace adapter was *NOT* called
    mock_marketplace_adapter.submit_listing.assert_not_called()


@pytest.mark.asyncio
async def test_list_item_product_not_found(
    listing_service: ListingService,
    mock_promotional_rule_repo: MagicMock,
    mock_marketplace_adapter: MagicMock,
    mock_inventory_product_repo: MagicMock,
    mock_variable_product_repo: MagicMock,
    mock_assembly_repo: MagicMock,
    mock_service_product_repo: MagicMock,
    mocker,  # Use pytest-mock's mocker fixture for patching
):
    """
    Test listing when the product identifier is not found in the repository.
    """
    # Arrange: Configure the product repo mock to return None
    rule_id = 1
    test_sku = "UNKNOWN-SKU"
    marketplace_name = "TestPlace"
    mock_rule = PromotionalRule(
        id=rule_id,
        product_identifier=test_sku,
        marketplace_name=marketplace_name,
        product_type=ProductTypeEnum.INVENTORY.value,
        is_active=True,
        marketplace_specific_settings={"setting": "value"},
    )
    mock_promotional_rule_repo.get = AsyncMock(return_value=mock_rule)
    mock_inventory_product_repo.get_by_sku = AsyncMock(return_value=None)
    mock_variable_product_repo.get_by_group_id = AsyncMock(return_value=None)
    mock_assembly_repo.get_by_sku = AsyncMock(return_value=None)
    mock_service_product_repo.get_by_sku = AsyncMock(return_value=None)

    # Act: Call the service method
    actual_listing_id = await listing_service.list_item_on_marketplace(rule_id=rule_id)

    # Assert: Check the outcome
    # 1. Return value should be None
    assert actual_listing_id is None

    # 2. Verify the promotional rule repository's get method was called
    mock_promotional_rule_repo.get.assert_awaited_once_with(rule_id)

    # 3. Verify the product repository was called
    mock_inventory_product_repo.get_by_sku.assert_awaited_once_with(test_sku)

    # 4. Verify the marketplace adapter was *NOT* called (since product wasn't found)
    mock_marketplace_adapter.submit_listing.assert_not_called()


@pytest.mark.asyncio
async def test_list_item_marketplace_not_found(
    mock_promotional_rule_repo: MagicMock,
    mock_listing_repo: MagicMock,
    mock_marketplace_adapter: MagicMock,
):
    """
    Test listing when the marketplace name is not found in configured adapters.
    """
    # Arrange:
    rule_id = 1
    test_sku = "TEST-SKU-01"
    # Completely fictional case, because we don't have a real marketplace that is not found
    marketplace_name = "NonExistentPlace"
    mock_rule = PromotionalRule(
        id=rule_id,
        product_identifier=test_sku,
        marketplace_name=marketplace_name,
        product_type=ProductTypeEnum.INVENTORY.value,
        is_active=True,
        marketplace_specific_settings={"setting": "value"},
    )
    mock_promotional_rule_repo.get.return_value = mock_rule
    mock_inventory_product_repo.get_by_sku = AsyncMock(return_value=None)
    mock_variable_product_repo.get_by_group_id = AsyncMock(return_value=None)
    mock_assembly_repo.get_by_sku = AsyncMock(return_value=None)
    mock_service_product_repo.get_by_sku = AsyncMock(return_value=None)

    # Arrange: Create ListingService with an empty adapter dictionary
    # We still inject mock_product_repo to potentially check it wasn't called.
    # The specific mock_marketplace_adapter isn't used here, but the fixture runs.
    service_with_no_adapters = ListingService(
        mock_promotional_rule_repo,
        mock_inventory_product_repo,
        mock_variable_product_repo,
        mock_assembly_repo,
        mock_service_product_repo,
        mock_listing_repo,
        marketplace_adapters={},  # Empty dict - no adapters configured
    )

    # Act: Call the service method with a marketplace name that won't be found
    actual_listing_id = await service_with_no_adapters.list_item_on_marketplace(
        rule_id=rule_id
    )

    # Assert: Check the outcome
    # 1. Return value should be None
    assert actual_listing_id is None

    # 2. Verify the promotional rule repository was called
    mock_promotional_rule_repo.get.assert_called_once_with(rule_id)

    # 3. Verify the product repository was *NOT* called
    mock_inventory_product_repo.get_by_sku.assert_called_once_with(test_sku)
    mock_variable_product_repo.get_by_group_id.assert_not_called()
    mock_assembly_repo.get_by_sku.assert_not_called()
    mock_service_product_repo.get_by_sku.assert_not_called()

    # 4. Verify the marketplace adapter was *NOT* called
    # (We can check the fixture mock, even though it wasn't in the dict,
    #  to be absolutely sure no adapter logic ran)
    mock_marketplace_adapter.submit_listing.assert_not_called()


@pytest.mark.asyncio
async def test_list_item_listing_error(
    listing_service: ListingService,
    mock_promotional_rule_repo: MagicMock,
    mock_listing_repo: MagicMock,
    mock_marketplace_adapter: MagicMock,
    mocker,  # Use pytest-mock's mocker fixture for patching
):
    """
    Test listing when the marketplace adapter raises a ListingError.
    """
    # Arrange: Configure mocks
    rule_id = 1
    test_sku = "TEST-SKU-001"
    marketplace_name = "TestPlace"
    mock_product = InventoryProduct(sku=test_sku, title="Test Item", price=20.0)
    mock_rule = PromotionalRule(
        id=rule_id,
        product_identifier=test_sku,
        marketplace_name=marketplace_name,
        product_type=ProductTypeEnum.INVENTORY.value,
        is_active=True,
        marketplace_specific_settings={"setting": "value"},
    )
    mock_promotional_rule_repo.get.return_value = mock_rule
    # Mock the internal helper method to isolate list_item_on_marketplace logic
    mock_get_product_data_and_rule = mocker.patch.object(
        listing_service,
        "_get_product_data_and_rule",
        new_callable=AsyncMock,
        return_value=(mock_product, mock_rule),
    )

    # 1. Configure adapter's submit_listing to RAISE ListingError
    mock_marketplace_adapter.submit_listing.side_effect = ListingError(
        "Mocked listing error"
    )

    # Act: Call the service method
    actual_listing_id = await listing_service.list_item_on_marketplace(rule_id=rule_id)

    # Assert: Check the outcome
    # 1. Return value should be None as the listing failed
    assert actual_listing_id is None

    # 2. Verify the internal call to get product data and rule was made
    mock_get_product_data_and_rule.assert_awaited_once_with(rule_id)

    # 3. Verify the marketplace adapter's submit_listing method *was* called
    #    (even though it immediately raised an error)
    mock_marketplace_adapter.submit_listing.assert_awaited_once_with(
        mock_product, listing_config=mock_rule.marketplace_specific_settings
    )


@pytest.mark.asyncio
async def test_list_item_other_exception(
    listing_service: ListingService,
    mock_promotional_rule_repo: MagicMock,
    mock_listing_repo: MagicMock,
    mock_marketplace_adapter: MagicMock,
    mocker,  # Use pytest-mock's mocker fixture for patching
):
    """
    Test listing when the marketplace adapter raises an unexpected Exception.
    """
    # Arrange: Configure mocks
    rule_id = 1
    test_sku = "TEST-SKU-GEN-ERR"
    marketplace_name = "TestPlace"
    mock_product = InventoryProduct(sku=test_sku, title="Test Item", price=20.0)
    mock_rule = PromotionalRule(
        id=rule_id,
        product_identifier=test_sku,
        marketplace_name=marketplace_name,
        product_type=ProductTypeEnum.INVENTORY.value,
        is_active=True,
        marketplace_specific_settings={"setting": "value"},
    )
    mock_promotional_rule_repo.get.return_value = mock_rule
    # Mock the internal helper method to isolate list_item_on_marketplace logic
    mock_get_product_data_and_rule = mocker.patch.object(
        listing_service,
        "_get_product_data_and_rule",
        new_callable=AsyncMock,
        return_value=(mock_product, mock_rule),
    )

    # 2. Configure adapter's submit_listing to RAISE a generic Exception
    mock_marketplace_adapter.submit_listing.side_effect = Exception(
        "Mocked unexpected error"
    )

    # Act: Call the service method
    actual_listing_id = await listing_service.list_item_on_marketplace(rule_id=rule_id)

    # Assert: Check the outcome
    # 1. Return value should be None
    assert actual_listing_id is None

    # 2. Verify the internal call to get product data and rule was made
    mock_get_product_data_and_rule.assert_awaited_once_with(rule_id)

    # 3. Verify the marketplace adapter's submit_listing method *was* called
    mock_marketplace_adapter.submit_listing.assert_awaited_once_with(
        mock_product, listing_config=mock_rule.marketplace_specific_settings
    )


@pytest.mark.asyncio
async def test_list_item_success_repo_save_fails(
    listing_service: ListingService,
    mock_promotional_rule_repo: MagicMock,
    mock_listing_repo: MagicMock,
    mock_marketplace_adapter: MagicMock,
    mocker,  # Use pytest-mock's mocker fixture for patching
):
    """
    Test successful listing submission but failure when saving to listing repo.
    """
    # Arrange: Configure mocks
    rule_id = 1
    test_sku = "TEST-SKU-REPO-FAIL"
    marketplace_name = "TestPlace"
    expected_listing_id = "MOCK-LISTING-999"
    mock_product = InventoryProduct(sku=test_sku, title="Repo Fail Item", price=5.0)
    mock_rule = PromotionalRule(
        id=rule_id,
        product_identifier=test_sku,
        marketplace_name=marketplace_name,
        product_type=ProductTypeEnum.INVENTORY.value,
        is_active=True,
        marketplace_specific_settings={"setting": "value"},
    )
    mock_promotional_rule_repo.get.return_value = mock_rule
    # Mock the internal helper method to isolate list_item_on_marketplace logic
    mock_get_product_data_and_rule = mocker.patch.object(
        listing_service,
        "_get_product_data_and_rule",
        new_callable=AsyncMock,
        return_value=(mock_product, mock_rule),
    )

    # 2. Configure adapter to return a success listing ID
    mock_marketplace_adapter.submit_listing = AsyncMock(
        return_value=expected_listing_id
    )  # Mock async method

    # 3. Configure Listing repo add_or_update to RAISE an error
    mock_listing_repo.add_or_update.side_effect = RuntimeError("Mocked repo save error")

    # Act: Call the service method
    actual_listing_id = await listing_service.list_item_on_marketplace(rule_id=rule_id)

    # Assert: Check the outcome
    # 1. Service should STILL return the listing ID received from the marketplace
    assert actual_listing_id == expected_listing_id

    # 2. Verify the internal call to get product data and rule was made
    mock_get_product_data_and_rule.assert_awaited_once_with(rule_id)

    # 3. Verify the marketplace adapter's submit_listing method was called
    mock_marketplace_adapter.submit_listing.assert_awaited_once_with(
        mock_product, listing_config=mock_rule.marketplace_specific_settings
    )

    # 4. Verify the listing repository's add_or_update method *was* called
    #    (even though it raised an error). Check it was called with a Listing object.
    mock_listing_repo.add.assert_awaited_once_with(ANY)  # ANY checks arg exists
    # More detailed check (optional): Check the type and key attributes of the Listing passed
    call_args, _ = mock_listing_repo.add.call_args
    assert len(call_args) == 1
    listing_arg = call_args[0]
    assert isinstance(listing_arg, Listing)
    assert listing_arg.rule_id == rule_id
    assert listing_arg.marketplace_name == marketplace_name
    assert listing_arg.marketplace_listing_id == expected_listing_id


@pytest.mark.asyncio
async def test_update_price_success(
    listing_service: ListingService,
    mock_marketplace_adapter: MagicMock,
):
    """Test successful price update call."""
    # Arrange
    listing_id = "MOCK-LISTING-123"
    marketplace_name = mock_marketplace_adapter.name  # Use name from mock
    sku = "TEST-SKU-01"
    new_price = 99.99

    # Configure mock adapter method (no return value, no exception)
    # We don't need to configure return_value=None explicitly for methods returning None
    # We also don't need side_effect if no exception is raised.
    # We DO need to ensure the mock object itself exists and is passed via fixture.

    # Act
    success = await listing_service.update_price_on_marketplace(
        listing_id=listing_id,
        marketplace_name=marketplace_name,
        sku=sku,
        new_price=new_price,
    )

    # Assert
    # 1. Check return value is True
    assert success is True

    # 2. Verify the adapter's update_listing_price method was called correctly
    mock_marketplace_adapter.update_listing_price.assert_called_once_with(
        listing_id, sku, new_price
    )


@pytest.mark.asyncio
async def test_update_price_marketplace_not_found(
    listing_service: ListingService,
    mock_marketplace_adapter: MagicMock,
):
    """Test price update when marketplace is not found."""
    # Arrange
    listing_id = "MOCK-LISTING-123"
    marketplace_name = "NonExistentPlace"
    sku = "TEST-SKU-01"
    new_price = 99.99

    # Act
    success = await listing_service.update_price_on_marketplace(
        listing_id=listing_id,
        marketplace_name=marketplace_name,
        sku=sku,
        new_price=new_price,
    )

    # Assert
    # 1. Check return value is False
    assert success is False
    # 2. Verify the adapter's update_listing_price method was not called
    mock_marketplace_adapter.update_listing_price.assert_not_called()


@pytest.mark.asyncio
async def test_update_price_listing_error(
    listing_service: ListingService,
    mock_marketplace_adapter: MagicMock,
):
    """Test price update when listing ID is not found."""
    # Arrange
    listing_id = "NON-EXISTING-LISTING"
    marketplace_name = mock_marketplace_adapter.name
    sku = "TEST-SKU-01"
    new_price = 99.99

    # Configure mock adapter to raise ListingError
    mock_marketplace_adapter.update_listing_price.side_effect = ListingError(
        "Mocked listing error"
    )

    # Act
    success = await listing_service.update_price_on_marketplace(
        listing_id=listing_id,
        marketplace_name=marketplace_name,
        sku=sku,
        new_price=new_price,
    )

    # Assert
    # 1. Check return value is False
    assert success is False

    # 2. Verify the adapter's update_listing_price method was called and raised an error
    mock_marketplace_adapter.update_listing_price.assert_called_once_with(
        listing_id, sku, new_price
    )


@pytest.mark.asyncio
async def test_update_price_other_exception(
    listing_service: ListingService,
    mock_marketplace_adapter: MagicMock,
):
    """Test price update when other exception is raised."""
    # Arrange
    listing_id = "MOCK-LISTING-123"
    marketplace_name = mock_marketplace_adapter.name
    sku = "TEST-SKU-01"
    new_price = 99.99

    # Configure mock adapter to raise unexpected Exception
    mock_marketplace_adapter.update_listing_price.side_effect = Exception(
        "Mocked unexpected error"
    )

    # Act
    success = await listing_service.update_price_on_marketplace(
        listing_id=listing_id,
        marketplace_name=marketplace_name,
        sku=sku,
        new_price=new_price,
    )

    # Assert
    # 1. Check return value is False
    assert success is False

    # 2. Verify the adapter's update_listing_price method was called and raised an error
    mock_marketplace_adapter.update_listing_price.assert_called_once_with(
        listing_id, sku, new_price
    )


# --- Tests for update_stock_on_marketplace ---
@pytest.mark.asyncio
async def test_update_stock_success(
    listing_service: ListingService,
    mock_marketplace_adapter: MagicMock,
):
    """Test successful stock update call."""
    # Arrange
    listing_id = "MOCK-LISTING-123"
    marketplace_name = mock_marketplace_adapter.name
    sku = "TEST-SKU-01"
    stock_update = {sku: 10}

    # Configure mock adapter method (no return value, no exception)
    # We don't need to configure return_value=None explicitly for methods returning None
    # We also don't need side_effect if no exception is raised.
    # We DO need to ensure the mock object itself exists and is passed via fixture.

    # Act
    success = await listing_service.update_stock_on_marketplace(
        listing_id=listing_id,
        marketplace_name=marketplace_name,
        sku_stock=stock_update,
    )

    # Assert
    # 1. Check return value is True
    assert success is True

    # 2. Verify the adapter's update_listing_stock method was called correctly
    mock_marketplace_adapter.update_listing_stock.assert_called_once_with(
        listing_id, stock_update
    )


@pytest.mark.asyncio
async def test_update_stock_marketplace_not_found(
    listing_service: ListingService,
    mock_marketplace_adapter: MagicMock,
):
    """Test stock update when marketplace is not found."""
    # Arrange
    listing_id = "MOCK-LISTING-123"
    marketplace_name = "NonExistentPlace"
    sku = "TEST-SKU-01"
    stock_update = {sku: 10}

    # Act
    success = await listing_service.update_stock_on_marketplace(
        listing_id=listing_id,
        marketplace_name=marketplace_name,
        sku_stock=stock_update,
    )

    # Assert
    # 1. Check return value is False
    assert success is False

    # 2. Verify the adapter's update_listing_stock method was not called
    mock_marketplace_adapter.update_listing_stock.assert_not_called()


@pytest.mark.asyncio
async def test_update_stock_listing_error(
    listing_service: ListingService,
    mock_marketplace_adapter: MagicMock,
):
    """Test stock update when listing ID is not found."""
    # Arrange
    listing_id = "NON-EXISTING-LISTING"
    marketplace_name = mock_marketplace_adapter.name
    sku = "TEST-SKU-01"
    stock_update = {sku: 10}

    # Configure mock adapter to raise ListingError
    mock_marketplace_adapter.update_listing_stock.side_effect = ListingError(
        "Mocked listing error"
    )

    # Act
    success = await listing_service.update_stock_on_marketplace(
        listing_id=listing_id,
        marketplace_name=marketplace_name,
        sku_stock=stock_update,
    )

    # Assert
    # 1. Check return value is False
    assert success is False

    # 2. Verify the adapter's update_listing_stock method was called and raised an error
    mock_marketplace_adapter.update_listing_stock.assert_called_once_with(
        listing_id, stock_update
    )


@pytest.mark.asyncio
async def test_update_stock_other_exception(
    listing_service: ListingService,
    mock_marketplace_adapter: MagicMock,
):
    """Test stock update when other exception is raised."""
    # Arrange
    listing_id = "MOCK-LISTING-123"
    marketplace_name = mock_marketplace_adapter.name
    sku = "TEST-SKU-01"
    stock_update = {sku: 10}

    # Configure mock adapter to raise unexpected Exception
    mock_marketplace_adapter.update_listing_stock.side_effect = Exception(
        "Mocked unexpected error"
    )

    # Act
    success = await listing_service.update_stock_on_marketplace(
        listing_id=listing_id,
        marketplace_name=marketplace_name,
        sku_stock=stock_update,
    )

    # Assert
    # 1. Check return value is False
    assert success is False

    # 2. Verify the adapter's update_listing_stock method was called and raised an error
    mock_marketplace_adapter.update_listing_stock.assert_called_once_with(
        listing_id, stock_update
    )
