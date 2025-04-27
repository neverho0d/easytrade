# tests/services/test_listing_service.py

import pytest
from unittest.mock import (
    ANY,
    MagicMock,
)  # Can use MagicMock directly or pytest-mock fixture

# Import the code to be tested and the interfaces to be mocked
from marketplace_aggregator.models.listing import Listing
from marketplace_aggregator.repositories.listing_repo import ListingRepository
from marketplace_aggregator.services.listing_service import ListingService
from marketplace_aggregator.repositories.product_repo import (
    ProductRepository,
)
from marketplace_aggregator.adapters.marketplace import Marketplace, ListingError
from marketplace_aggregator.models.product import InventoryProduct  # For test data


# --- Pytest Fixtures for Setup ---


@pytest.fixture
def mock_product_repo() -> MagicMock:
    """Creates a mock ProductRepository."""
    # Create a mock object that adheres to the ProductRepository interface
    # 'spec=ProductRepository' ensures mock only has methods defined in the interface
    mock_repo = MagicMock(spec=ProductRepository)
    return mock_repo


@pytest.fixture
def mock_listing_repo() -> MagicMock:
    """Creates a mock ListingRepository."""
    mock_repo = MagicMock(spec=ListingRepository)
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
    mock_product_repo, mock_listing_repo, mock_marketplace_adapter
) -> ListingService:
    """Creates a ListingService instance with mocked dependencies."""
    # Create the dictionary of adapters to inject
    adapters = {mock_marketplace_adapter.name: mock_marketplace_adapter}
    # Inject the mocks into the service instance
    service = ListingService(
        product_repo=mock_product_repo,
        listing_repo=mock_listing_repo,
        marketplace_adapters=adapters,
    )
    return service


# --- Test Cases ---


def test_list_item_success(
    listing_service, mock_product_repo, mock_listing_repo, mock_marketplace_adapter
):
    """
    Test the successful path for listing an item.
    """
    # Arrange: Configure the mocks
    test_sku = "TEST-SKU-01"
    marketplace_name = "TestPlace"
    expected_listing_id = "MOCK-LISTING-123"

    # Create sample product data to be returned by the repo mock
    # Create an instance of InventoryProduct (or VariableProduct)
    #       Make sure it has a .sku or .group_id attribute matching test_sku
    test_product = InventoryProduct(sku=test_sku, title="Test Item", price=10.0)

    # Configure mock_product_repo.get() to return the test product
    # when called with test_sku
    # Use mock_product_repo.get.return_value = ...
    mock_product_repo.get.return_value = test_product

    # Configure mock_marketplace_adapter.submit_listing() to return
    # the expected listing ID when called with the test product
    # Use mock_marketplace_adapter.submit_listing.return_value = ...
    mock_marketplace_adapter.submit_listing.return_value = expected_listing_id

    # Act: Call the service method under test
    # Call listing_service.list_item_on_marketplace(...) and store the result
    actual_listing_id = listing_service.list_item_on_marketplace(
        product_identifier=test_sku, marketplace_name=marketplace_name
    )

    # Assert: Check the results and mock interactions
    # 1. Check the returned listing ID is correct
    assert actual_listing_id == expected_listing_id

    # 2. Verify the product repository's get method was called correctly
    mock_product_repo.get.assert_called_once_with(test_sku)

    # 3. Verify the marketplace adapter's submit_listing method was called correctly
    mock_marketplace_adapter.submit_listing.assert_called_once_with(test_product)


def test_list_item_product_not_found(
    listing_service, mock_product_repo, mock_marketplace_adapter
):
    """
    Test listing when the product identifier is not found in the repository.
    """
    # Arrange: Configure the product repo mock to return None
    test_sku = "UNKNOWN-SKU"
    marketplace_name = "TestPlace"
    mock_product_repo.get.return_value = None  # Simulate product not found

    # Act: Call the service method
    actual_listing_id = listing_service.list_item_on_marketplace(
        product_identifier=test_sku, marketplace_name=marketplace_name
    )

    # Assert: Check the outcome
    # 1. Return value should be None
    assert actual_listing_id is None

    # 2. Verify the product repository's get method was called
    mock_product_repo.get.assert_called_once_with(test_sku)

    # 3. Verify the marketplace adapter was *NOT* called (since product wasn't found)
    mock_marketplace_adapter.submit_listing.assert_not_called()


def test_list_item_marketplace_not_found(
    mock_product_repo, mock_listing_repo, mock_marketplace_adapter
):
    """
    Test listing when the marketplace name is not found in configured adapters.
    """
    # Arrange: Create ListingService with an empty adapter dictionary
    # We still inject mock_product_repo to potentially check it wasn't called.
    # The specific mock_marketplace_adapter isn't used here, but the fixture runs.
    service_with_no_adapters = ListingService(
        product_repo=mock_product_repo,
        listing_repo=mock_listing_repo,
        marketplace_adapters={},  # Empty dict - no adapters configured
    )
    test_sku = "TEST-SKU-01"
    marketplace_name = "NonExistentPlace"

    # Act: Call the service method with a marketplace name that won't be found
    actual_listing_id = service_with_no_adapters.list_item_on_marketplace(
        product_identifier=test_sku, marketplace_name=marketplace_name
    )

    # Assert: Check the outcome
    # 1. Return value should be None
    assert actual_listing_id is None

    # 2. Verify the product repository was *NOT* called
    mock_product_repo.get.assert_not_called()

    # 3. Verify the marketplace adapter was *NOT* called
    # (We can check the fixture mock, even though it wasn't in the dict,
    #  to be absolutely sure no adapter logic ran)
    mock_marketplace_adapter.submit_listing.assert_not_called()


def test_list_item_listing_error(
    listing_service, mock_product_repo, mock_marketplace_adapter
):
    """
    Test listing when the marketplace adapter raises a ListingError.
    """
    # Arrange: Configure mocks
    test_sku = "TEST-SKU-ERR"
    marketplace_name = "TestPlace"
    test_product = InventoryProduct(sku=test_sku, title="Error Item", price=20.0)
    error_message = "Mock API validation failed"

    # 1. Configure repo to return the product
    mock_product_repo.get.return_value = test_product

    # 2. Configure adapter's submit_listing to RAISE ListingError
    #    Use the 'side_effect' attribute for raising exceptions
    mock_marketplace_adapter.submit_listing.side_effect = ListingError(error_message)

    # Act: Call the service method
    actual_listing_id = listing_service.list_item_on_marketplace(
        product_identifier=test_sku, marketplace_name=marketplace_name
    )

    # Assert: Check the outcome
    # 1. Return value should be None as the listing failed
    assert actual_listing_id is None

    # 2. Verify the product repository's get method was called
    mock_product_repo.get.assert_called_once_with(test_sku)

    # 3. Verify the marketplace adapter's submit_listing method *was* called
    #    (even though it immediately raised an error)
    mock_marketplace_adapter.submit_listing.assert_called_once_with(test_product)


def test_list_item_other_exception(
    listing_service, mock_product_repo, mock_marketplace_adapter
):
    """
    Test listing when the marketplace adapter raises an unexpected Exception.
    """
    # Arrange: Configure mocks
    test_sku = "TEST-SKU-GEN-ERR"
    marketplace_name = "TestPlace"
    test_product = InventoryProduct(
        sku=test_sku, title="General Error Item", price=30.0
    )
    error_message = "Something unexpected broke!"

    # 1. Configure repo to return the product
    mock_product_repo.get.return_value = test_product

    # 2. Configure adapter's submit_listing to RAISE a generic Exception
    mock_marketplace_adapter.submit_listing.side_effect = Exception(error_message)

    # Act: Call the service method
    actual_listing_id = listing_service.list_item_on_marketplace(
        product_identifier=test_sku, marketplace_name=marketplace_name
    )

    # Assert: Check the outcome
    # 1. Return value should be None
    assert actual_listing_id is None

    # 2. Verify the product repository's get method was called
    mock_product_repo.get.assert_called_once_with(test_sku)

    # 3. Verify the marketplace adapter's submit_listing method *was* called
    mock_marketplace_adapter.submit_listing.assert_called_once_with(test_product)


def test_list_item_success_repo_save_fails(
    listing_service, mock_product_repo, mock_listing_repo, mock_marketplace_adapter
):
    """
    Test successful listing submission but failure when saving to listing repo.
    """
    # Arrange: Configure mocks
    test_sku = "TEST-SKU-REPO-FAIL"
    marketplace_name = "TestPlace"
    expected_listing_id = "MOCK-LISTING-999"
    test_product = InventoryProduct(sku=test_sku, title="Repo Fail Item", price=5.0)
    repo_error_message = "Simulated DB connection error"

    # 1. Configure repo to return the product
    mock_product_repo.get.return_value = test_product

    # 2. Configure adapter to return a success listing ID
    mock_marketplace_adapter.submit_listing.return_value = expected_listing_id

    # 3. Configure Listing repo add_or_update to RAISE an error
    mock_listing_repo.add_or_update.side_effect = RuntimeError(repo_error_message)

    # Act: Call the service method
    actual_listing_id = listing_service.list_item_on_marketplace(
        product_identifier=test_sku, marketplace_name=marketplace_name
    )

    # Assert: Check the outcome
    # 1. Service should STILL return the listing ID received from the marketplace
    assert actual_listing_id == expected_listing_id

    # 2. Verify the product repository's get method was called
    mock_product_repo.get.assert_called_once_with(test_sku)

    # 3. Verify the marketplace adapter's submit_listing method was called
    mock_marketplace_adapter.submit_listing.assert_called_once_with(test_product)

    # 4. Verify the listing repository's add_or_update method *was* called
    #    (even though it raised an error). Check it was called with a Listing object.
    mock_listing_repo.add_or_update.assert_called_once_with(
        ANY
    )  # ANY checks arg exists
    # More detailed check (optional): Check the type and key attributes of the Listing passed
    call_args, _ = mock_listing_repo.add_or_update.call_args
    assert len(call_args) == 1
    listing_arg = call_args[0]
    assert isinstance(listing_arg, Listing)
    assert listing_arg.rule_id == test_sku
    assert listing_arg.marketplace_name == marketplace_name
    assert listing_arg.marketplace_listing_id == expected_listing_id


def test_update_price_success(listing_service, mock_marketplace_adapter):
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
    success = listing_service.update_price_on_marketplace(
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


def test_update_price_marketplace_not_found(listing_service, mock_marketplace_adapter):
    """Test price update when marketplace is not found."""
    # Arrange
    listing_id = "MOCK-LISTING-123"
    marketplace_name = "NonExistentPlace"
    sku = "TEST-SKU-01"
    new_price = 99.99

    # Act
    success = listing_service.update_price_on_marketplace(
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


def test_update_price_listing_error(listing_service, mock_marketplace_adapter):
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
    success = listing_service.update_price_on_marketplace(
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


def test_update_price_other_exception(listing_service, mock_marketplace_adapter):
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
    success = listing_service.update_price_on_marketplace(
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
def test_update_stock_success(listing_service, mock_marketplace_adapter):
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
    success = listing_service.update_stock_on_marketplace(
        listing_id=listing_id, marketplace_name=marketplace_name, sku_stock=stock_update
    )

    # Assert
    # 1. Check return value is True
    assert success is True

    # 2. Verify the adapter's update_listing_stock method was called correctly
    mock_marketplace_adapter.update_listing_stock.assert_called_once_with(
        listing_id, stock_update
    )


def test_update_stock_marketplace_not_found(listing_service, mock_marketplace_adapter):
    """Test stock update when marketplace is not found."""
    # Arrange
    listing_id = "MOCK-LISTING-123"
    marketplace_name = "NonExistentPlace"
    sku = "TEST-SKU-01"
    stock_update = {sku: 10}

    # Act
    success = listing_service.update_stock_on_marketplace(
        listing_id=listing_id, marketplace_name=marketplace_name, sku_stock=stock_update
    )

    # Assert
    # 1. Check return value is False
    assert success is False

    # 2. Verify the adapter's update_listing_stock method was not called
    mock_marketplace_adapter.update_listing_stock.assert_not_called()


def test_update_stock_listing_error(listing_service, mock_marketplace_adapter):
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
    success = listing_service.update_stock_on_marketplace(
        listing_id=listing_id, marketplace_name=marketplace_name, sku_stock=stock_update
    )

    # Assert
    # 1. Check return value is False
    assert success is False

    # 2. Verify the adapter's update_listing_stock method was called and raised an error
    mock_marketplace_adapter.update_listing_stock.assert_called_once_with(
        listing_id, stock_update
    )


def test_update_stock_other_exception(listing_service, mock_marketplace_adapter):
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
    success = listing_service.update_stock_on_marketplace(
        listing_id=listing_id, marketplace_name=marketplace_name, sku_stock=stock_update
    )

    # Assert
    # 1. Check return value is False
    assert success is False

    # 2. Verify the adapter's update_listing_stock method was called and raised an error
    mock_marketplace_adapter.update_listing_stock.assert_called_once_with(
        listing_id, stock_update
    )
