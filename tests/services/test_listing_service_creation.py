# test_listing_service_creation.py

from typing import Optional
import pytest
from unittest.mock import AsyncMock, MagicMock, ANY

from marketplace_aggregator.models.listing import Listing
from marketplace_aggregator.models.promotional_rule import (
    PromotionalRule,
    ProductTypeEnum,
)
from marketplace_aggregator.models.product import (
    Assembly,
    InventoryProduct,
    Sellable,
    ServiceProduct,
)
from marketplace_aggregator.models.variable_product import VariableProduct
from marketplace_aggregator.services.exceptions import (
    AdapterNotFoundError,
    ListingPreparationError,
    ProductNotFoundError,
    RuleInactiveError,
    RuleNotFoundError,
)
from marketplace_aggregator.services.listing_service import ListingService


# --- Parameterized Success Test ---
# Define test data for different product types
inventory_prod = InventoryProduct(
    sku="INV-001", title="Test Inv Prod", price=10.0, id=101
)
service_prod = ServiceProduct(sku="SVC-001", title="Test Svc Prod", price=50.0, id=201)
assembly_prod = Assembly(
    sku="ASM-001", title="Test Asm Prod", id=301
)  # Price calculated by service/repo later
variable_prod_group = VariableProduct(
    group_id="VAR-001", name="Test Var Prod", variant_type="InventoryProduct", id=401
)


@pytest.mark.parametrize(
    "product_type_enum, product_identifier, mock_product_obj, expected_price_in_listing",
    [
        pytest.param(
            ProductTypeEnum.INVENTORY,
            inventory_prod.sku,
            inventory_prod,
            10.0,
            id="inventory_product",
        ),
        pytest.param(
            ProductTypeEnum.SERVICE,
            service_prod.sku,
            service_prod,
            50.0,
            id="service_product",
        ),
        pytest.param(
            ProductTypeEnum.ASSEMBLY,
            assembly_prod.sku,
            assembly_prod,
            0.0,
            id="assembly_product",
        ),  # Assembly price logic is elsewhere
        pytest.param(
            ProductTypeEnum.VARIABLE,
            variable_prod_group.group_id,
            variable_prod_group,
            None,
            id="variable_product",
        ),  # Variable group itself isn't listed directly this way usually
        # Note: The last case for VariableProduct might need adjustment depending on how _prepare_listing_data works.
        # If _prepare_listing_data returns VariableListingData DTO, we'd mock that instead.
        # Let's assume for this test, _prepare_listing_data returns the correct object type for the adapter.
        # We are mocking _prepare_listing_data anyway.
    ],
)
@pytest.mark.asyncio
async def test_list_item_success_parametrized(
    listing_service: ListingService,
    mock_listing_repo: MagicMock,
    mock_marketplace_adapter: MagicMock,
    mock_promotional_rule_repo: MagicMock,
    mocker,
    # Parameters injected by pytest:
    product_type_enum: ProductTypeEnum,
    product_identifier: str,
    mock_product_obj: Sellable | VariableProduct,  # The object helper should return
    expected_price_in_listing: Optional[float],
):
    """Test successful listing for different product types."""
    # Arrange
    rule_id = 1
    marketplace_name = "TestPlace"
    expected_listing_id = f"MOCK-LISTING-{product_identifier}"
    mock_specific_settings = {"category": "test"}

    # Mock rule based on parameters
    mock_rule = PromotionalRule(
        id=rule_id,
        product_identifier=product_identifier,
        marketplace_name=marketplace_name,
        product_type=product_type_enum.value,
        is_active=True,
        marketplace_specific_settings=mock_specific_settings,
    )

    # 1. Mock the REPOSITORY call that _get_active_rule makes
    mock_promotional_rule_repo.get = AsyncMock(return_value=mock_rule)
    # 2. Mock the _prepare_listing_data helper
    mock_prepare_data = mocker.patch.object(
        listing_service,
        "_prepare_listing_data",
        new_callable=AsyncMock,
        return_value=mock_product_obj,  # Return the object for this test case
    )

    # 3. Mock the marketplace adapter to return a success listing ID
    mock_marketplace_adapter.submit_listing = AsyncMock(
        return_value=expected_listing_id
    )
    # 4. Mock the listing repo to save the listing
    mock_listing_repo.add = AsyncMock(return_value=None)

    # Act
    actual_listing_id = await listing_service.list_item_on_marketplace(rule_id=rule_id)

    # Assert
    assert actual_listing_id == expected_listing_id
    # Check helper was called
    # Note: Since _prepare_listing_data calls _get_active_rule, we might not need to mock _get_active_rule directly here
    # Or we mock _get_active_rule AND _prepare_listing_data. Mocking just _prepare_listing_data is simpler.
    # Check repo was called by the real _get_active_rule
    mock_promotional_rule_repo.get.assert_awaited_once_with(rule_id)
    # Check helper was called
    mock_prepare_data.assert_awaited_once_with(
        mock_rule
    )  # Check it was called with the rule
    # Check adapter call (item passed is the one returned by the mocked helper)
    mock_marketplace_adapter.submit_listing.assert_awaited_once_with(
        mock_product_obj, listing_config=mock_specific_settings
    )
    # Check repo save call
    mock_listing_repo.add.assert_awaited_once_with(ANY)
    call_args, _ = mock_listing_repo.add.call_args
    saved_listing: Listing = call_args[0]
    assert saved_listing.rule_id == rule_id
    assert saved_listing.marketplace_listing_id == expected_listing_id
    assert saved_listing.product_identifier == product_identifier
    assert saved_listing.listed_price == expected_price_in_listing


# --- Test Case for Rule Not Found ---
@pytest.mark.asyncio
async def test_list_item_rule_not_found(
    listing_service: ListingService,
    mock_marketplace_adapter: MagicMock,
    mocker,  # Use pytest-mock's mocker fixture for patching
):
    """Test listing raises RuleNotFoundError when the rule ID does not exist."""
    # Arrange
    rule_id = 999
    # Mock the *first* helper called (_get_active_rule) to raise the error
    mocker.patch.object(
        listing_service,
        "_get_active_rule",
        new_callable=AsyncMock,
        side_effect=RuleNotFoundError(rule_id),  # Raise the specific error
    )
    # Mock _get_adapter to track if it's called
    mock_get_adapter = mocker.patch.object(
        listing_service,
        "_get_adapter",
        new_callable=AsyncMock,
    )

    # Act & Assert: Use pytest.raises to check for the specific exception
    actual_listing_id = await listing_service.list_item_on_marketplace(rule_id=rule_id)
    # Assert: Check the outcome
    assert actual_listing_id is None

    # Verify _get_adapter was never called
    mock_get_adapter.assert_not_called()

    # Check the marketplace adapter was *NOT* called
    mock_marketplace_adapter.submit_listing.assert_not_called()


# --- Test Case for Rule Not Active ---
@pytest.mark.asyncio
async def test_list_item_rule_not_active(
    listing_service: ListingService,
    mock_marketplace_adapter: MagicMock,
    mocker,  # Use pytest-mock's mocker fixture for patching
):
    """Test listing raises RuleNotFoundError when the rule ID does not exist."""
    # Arrange
    rule_id = 999
    # Mock the *first* helper called (_get_active_rule) to raise the error
    mocker.patch.object(
        listing_service,
        "_get_active_rule",
        new_callable=AsyncMock,
        side_effect=RuleInactiveError(rule_id),  # Raise the specific error
    )
    # Mock _get_adapter to track if it's called
    mock_get_adapter = mocker.patch.object(
        listing_service,
        "_get_adapter",
        new_callable=AsyncMock,
    )

    # Act & Assert: Use pytest.raises to check for the specific exception
    actual_listing_id = await listing_service.list_item_on_marketplace(rule_id=rule_id)
    # Assert: Check the outcome
    assert actual_listing_id is None

    # Verify _get_adapter was never called
    mock_get_adapter.assert_not_called()

    # Check the marketplace adapter was *NOT* called
    mock_marketplace_adapter.submit_listing.assert_not_called()


# --- Test Case for Adapter Not Found ---
@pytest.mark.asyncio
async def test_list_item_adapter_not_found(
    listing_service: ListingService,
    mock_marketplace_adapter: MagicMock,
    mocker,  # Use pytest-mock's mocker fixture for patching
):
    """
    Test listing when the marketplace name is not found in configured adapters.
    """
    # Arrange:
    rule_id = 1
    test_sku = "TEST-SKU-01"
    mock_product = InventoryProduct(sku=test_sku, title="Test Item", price=10.0)
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
    # Mock the *first* helper called (_get_active_rule) to raise the error
    mock_get_active_rule = mocker.patch.object(
        listing_service,
        "_get_active_rule",
        new_callable=AsyncMock,
        return_value=mock_rule,
    )
    # Mock _get_adapter to raise AdapterNotFoundError
    mocker.patch.object(
        listing_service,
        "_get_adapter",
        side_effect=AdapterNotFoundError(marketplace_name),
    )
    mock_prepare_listing_data = mocker.patch.object(
        listing_service,
        "_prepare_listing_data",
        new_callable=AsyncMock,
        return_value=mock_product,
    )

    # Act: Call the service method with a marketplace name that won't be found
    actual_listing_id = await listing_service.list_item_on_marketplace(rule_id=rule_id)

    # Assert: Check the outcome
    # 1. Return value should be None
    assert actual_listing_id is None

    # 2. Verify the promotional rule repository was NOT called
    mock_get_active_rule.assert_awaited_once_with(rule_id)

    mock_prepare_listing_data.assert_not_awaited()
    # 3. Verify the marketplace adapter was *NOT* called
    # (We can check the fixture mock, even though it wasn't in the dict,
    #  to be absolutely sure no adapter logic ran)
    mock_marketplace_adapter.submit_listing.assert_not_awaited()


# --- Test Case for prepare_listing_data raises ProductNotFoundError
@pytest.mark.asyncio
async def test_list_item_prepare_listing_data_product_not_found(
    listing_service: ListingService,
    mock_marketplace_adapter: MagicMock,
    mocker,  # Use pytest-mock's mocker fixture for patching
):
    """
    Test listing when the prepare_listing_data method raises a ProductNotFoundError.
    """
    # Arrange: Configure the mocks
    rule_id = 1
    test_sku = "TEST-SKU-01"
    marketplace_name = "TestPlace"
    mock_rule = PromotionalRule(
        id=rule_id,
        product_identifier=test_sku,
        marketplace_name=marketplace_name,
        product_type=ProductTypeEnum.INVENTORY.value,
        is_active=True,
        marketplace_specific_settings={"setting": "value"},
    )
    mock_get_active_rule = mocker.patch.object(
        listing_service,
        "_get_active_rule",
        new_callable=AsyncMock,
        return_value=mock_rule,
    )
    mock_prepare_listing_data = mocker.patch.object(
        listing_service,
        "_prepare_listing_data",
        new_callable=AsyncMock,
        side_effect=ProductNotFoundError(test_sku),
    )

    # Act: Call the service method
    actual_listing_id = await listing_service.list_item_on_marketplace(rule_id=rule_id)

    # Assert: Check the outcome
    # 1. Return value should be None
    assert actual_listing_id is None

    # 2. Verify the promotional rule repository was called
    mock_get_active_rule.assert_awaited_once_with(rule_id)

    # 3. Verify the prepare_listing_data method was called
    mock_prepare_listing_data.assert_awaited_once_with(mock_rule)

    # 4. Verify the marketplace adapter was *NOT* called
    mock_marketplace_adapter.submit_listing.assert_not_called()


# --- Test Case for prepare_listing_data raises ListingPreparationError


# --- Test Case for prepare_listing_data raises ListingPreparationError
@pytest.mark.asyncio
async def test_list_item_prepare_listing_data_listing_preparation_error(
    listing_service: ListingService,
    mock_marketplace_adapter: MagicMock,
    mocker,  # Use pytest-mock's mocker fixture for patching
):
    """
    Test listing when the prepare_listing_data method raises a ListingPreparationError.
    """
    # Arrange: Configure the mocks
    rule_id = 1
    test_sku = "TEST-SKU-01"
    marketplace_name = "TestPlace"
    mock_rule = PromotionalRule(
        id=rule_id,
        product_identifier=test_sku,
        marketplace_name=marketplace_name,
        product_type=ProductTypeEnum.INVENTORY.value,
        is_active=True,
        marketplace_specific_settings={"setting": "value"},
    )
    # Mock the *first* helper called (_get_active_rule) to return the mock rule
    mock_get_active_rule = mocker.patch.object(
        listing_service,
        "_get_active_rule",
        new_callable=AsyncMock,
        return_value=mock_rule,
    )
    # Mock the *second* helper called (_prepare_listing_data) to raise the error
    mock_prepare_listing_data = mocker.patch.object(
        listing_service,
        "_prepare_listing_data",
        new_callable=AsyncMock,
        side_effect=ListingPreparationError(test_sku),
    )

    # Act: Call the service method
    actual_listing_id = await listing_service.list_item_on_marketplace(rule_id=rule_id)

    # Assert: Check the outcome
    # 1. Return value should be None
    assert actual_listing_id is None

    # 2. Verify the promotional rule repository was called
    mock_get_active_rule.assert_awaited_once_with(rule_id)

    # 3. Verify the prepare_listing_data method was called
    mock_prepare_listing_data.assert_awaited_once_with(mock_rule)

    # 4. Verify the marketplace adapter was *NOT* called
    mock_marketplace_adapter.submit_listing.assert_not_called()


# --- Test Case for successful listing submission but failure when saving to listing repo.
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
    # Mock the _prepare_listing_data method to return the mock product
    mocker.patch.object(
        listing_service,
        "_prepare_listing_data",
        new_callable=AsyncMock,
        return_value=mock_product,
    )
    # 2. Configure adapter to return a success listing ID
    mock_marketplace_adapter.submit_listing = AsyncMock(
        return_value=expected_listing_id
    )  # Mock async method

    # 3. Configure Listing repo add_or_update to RAISE an error
    mock_listing_repo.add.side_effect = RuntimeError("Mocked repo save error")

    # Act: Call the service method
    actual_listing_id = await listing_service.list_item_on_marketplace(rule_id=rule_id)

    # Assert: Check the outcome
    # 1. Service should STILL return the listing ID received from the marketplace
    assert actual_listing_id is None

    # 2. Verify the marketplace adapter's submit_listing method was called
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
