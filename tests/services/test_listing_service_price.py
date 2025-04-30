# tests/services/test_listing_service_price.py

import pytest
from unittest.mock import AsyncMock, MagicMock

# Import exceptions, models, service, etc.
from marketplace_aggregator.services.listing_service import ListingService
from marketplace_aggregator.adapters.marketplace import ListingError
from marketplace_aggregator.models.listing import Listing, ListingStateError # Import custom state error
# Import exceptions from the service layer
from marketplace_aggregator.services.exceptions import AdapterNotFoundError

# Use pytest-asyncio marker for all tests in this file
pytestmark = pytest.mark.asyncio


async def test_update_price_success(
    listing_service: ListingService,
    mock_listing_repo: MagicMock,
    mock_marketplace_adapter: MagicMock,
    mocker # For potentially spying on state method
):
    """Test successful price update when state allows it."""
    # Arrange
    rule_id = 1
    m_name = mock_marketplace_adapter.name
    l_id = "LIST-1"
    sku = "SKU1"
    new_price = 123.45

    # Mock the Listing object returned by the repo
    # Using a real object initialized to 'active' state
    mock_listing = Listing(
        id=1,
        rule_id=rule_id,
        product_identifier=sku,
        marketplace_name=m_name,
        marketplace_listing_id=l_id,
        status="active" # Start in active state
    )
    mock_listing.model_post_init(None) # Ensure state object is created

    # Configure repo mocks
    mock_listing_repo.get_by_composite_id = AsyncMock(return_value=mock_listing)
    mock_listing_repo.update = AsyncMock(return_value=mock_listing) # Simulate successful save

    # Configure adapter mock for success
    mock_marketplace_adapter.update_listing_price = AsyncMock(return_value=None)

    # Spy on the listing's state method to ensure it was called
    spy_listing_update_price = mocker.spy(mock_listing._state, "update_price")

    # Act
    success = await listing_service.update_price_on_marketplace(l_id, m_name, sku, new_price)

    # Assert
    assert success is True
    mock_listing_repo.get_by_composite_id.assert_awaited_once_with(m_name, l_id)
    spy_listing_update_price.assert_called_once_with(new_price) # Check state method called
    mock_marketplace_adapter.update_listing_price.assert_awaited_once_with(l_id, sku, new_price)
    mock_listing_repo.update.assert_awaited_once_with(mock_listing) # Check save was called
    assert mock_listing.listed_price == new_price # Verify internal state change


async def test_update_price_listing_not_found(
    listing_service: ListingService,
    mock_listing_repo: MagicMock,
    mock_marketplace_adapter: MagicMock
):
    """Test price update raises ListingRecordGetError if listing not found."""
    # Arrange
    m_name = "TestPlace"
    l_id = "LIST-NOT-FOUND"
    sku = "SKU1"
    new_price = 100.0
    # Configure repo to return None
    mock_listing_repo.get_by_composite_id = AsyncMock(return_value=None)

    # Act & Assert
    result = await listing_service.update_price_on_marketplace(l_id, m_name, sku, new_price)

    assert result is False
    mock_listing_repo.get_by_composite_id.assert_awaited_once_with(m_name, l_id)
    mock_marketplace_adapter.update_listing_price.assert_not_awaited()
    mock_listing_repo.update.assert_not_awaited()


async def test_update_price_state_disallows(
    listing_service: ListingService,
    mock_listing_repo: MagicMock,
    mock_marketplace_adapter: MagicMock,
    mocker
):
    """Test price update fails if the listing's state disallows it."""
    # Arrange
    rule_id = 1
    m_name = mock_marketplace_adapter.name
    l_id = "LIST-PENDING"
    sku = "SKU-PEND"
    new_price = 50.0
    # Create listing in a state (e.g., pending) that disallows price updates
    mock_listing = Listing(
        id=2,
        rule_id=rule_id,
        product_identifier=sku,
        marketplace_name=m_name,
        marketplace_listing_id=l_id,
        status="pending" # Pending state
    )
    mock_listing.model_post_init(None) # Initialize state object

    mock_listing_repo.get_by_composite_id = AsyncMock(return_value=mock_listing)

    # Mock the state method on the *actual state object* to raise the error
    mocker.patch.object(
        mock_listing._state, # Access the actual state object
        "update_price",
        side_effect=ListingStateError(f"Action 'update_price' not allowed in state '{mock_listing.current_status}'.")
    )

    # Act & Assert
    result = await listing_service.update_price_on_marketplace(l_id, m_name, sku, new_price)

    assert result is False
    mock_listing_repo.get_by_composite_id.assert_awaited_once_with(m_name, l_id)
    # Verify state method was called (implicitly checked by side_effect raising)
    mock_marketplace_adapter.update_listing_price.assert_not_awaited()
    mock_listing_repo.update.assert_not_awaited()


async def test_update_price_adapter_not_found(
    listing_service: ListingService,
    mock_listing_repo: MagicMock,
    mock_marketplace_adapter: MagicMock,
    mocker
):
    """Test price update raises AdapterNotFoundError if adapter isn't configured."""
    # Arrange
    rule_id = 1
    m_name = "UnknownPlace" # Marketplace name not in adapters map
    l_id = "LIST-1"
    sku = "SKU1"
    new_price = 123.45
    mock_listing = Listing(
        id=1,
        rule_id=rule_id,
        product_identifier=sku,
        marketplace_name=m_name,
        marketplace_listing_id=l_id,
        status="active"
    )
    mock_listing.model_post_init(None)
    mock_listing_repo.get_by_composite_id = AsyncMock(return_value=mock_listing)
    # Mock the service's internal helper directly
    mocker.patch.object(listing_service, "_get_adapter", side_effect=AdapterNotFoundError(m_name))

    # Act & Assert
    result = await listing_service.update_price_on_marketplace(l_id, m_name, sku, new_price)

    assert result is False
    mock_listing_repo.get_by_composite_id.assert_awaited_once_with(m_name, l_id)
    # Adapter update method should not have been reached
    mock_marketplace_adapter.update_listing_price.assert_not_awaited()


async def test_update_price_adapter_listing_error(
    listing_service: ListingService,
    mock_listing_repo: MagicMock,
    mock_marketplace_adapter: MagicMock
):
    """Test price update fails if the adapter raises ListingError."""
    # Arrange
    rule_id = 1
    m_name = mock_marketplace_adapter.name
    l_id = "LIST-1"
    sku = "SKU1"
    new_price = 123.45
    mock_listing = Listing(
        id=1,
        rule_id=rule_id,
        product_identifier=sku,
        marketplace_name=m_name,
        marketplace_listing_id=l_id,
        status="active"
    )
    mock_listing.model_post_init(None)

    mock_listing_repo.get_by_composite_id = AsyncMock(return_value=mock_listing)
    # Configure adapter to raise ListingError
    mock_marketplace_adapter.update_listing_price = AsyncMock(side_effect=ListingError("API Error"))
    mock_listing_repo.update = AsyncMock() # To check it's not called

    # Act & Assert
    result = await listing_service.update_price_on_marketplace(l_id, m_name, sku, new_price)

    assert result is False
    mock_listing_repo.get_by_composite_id.assert_awaited_once_with(m_name, l_id)
    mock_marketplace_adapter.update_listing_price.assert_awaited_once_with(l_id, sku, new_price)
    mock_listing_repo.update.assert_not_awaited() # Should fail before repo update


async def test_update_price_repo_update_fails(
    listing_service: ListingService,
    mock_listing_repo: MagicMock,
    mock_marketplace_adapter: MagicMock
):
    """Test price update fails if saving back to repo fails."""
    # Arrange
    rule_id = 1
    m_name = mock_marketplace_adapter.name
    l_id = "LIST-1"
    sku = "SKU1"
    new_price = 123.45
    mock_listing = Listing(
        id=1,
        rule_id=rule_id,
        product_identifier=sku,
        marketplace_name=m_name,
        marketplace_listing_id=l_id,
        status="active"
    )
    mock_listing.model_post_init(None)

    mock_listing_repo.get_by_composite_id = AsyncMock(return_value=mock_listing)
    mock_marketplace_adapter.update_listing_price = AsyncMock(return_value=None) # Adapter succeeds
    # Configure repo update to fail
    repo_error = RuntimeError("DB Save Failed")
    mock_listing_repo.update = AsyncMock(side_effect=repo_error)

    # Act & Assert
    result = await listing_service.update_price_on_marketplace(l_id, m_name, sku, new_price)

    assert result is False
    mock_listing_repo.get_by_composite_id.assert_awaited_once_with(m_name, l_id)
    mock_marketplace_adapter.update_listing_price.assert_awaited_once_with(l_id, sku, new_price)
    mock_listing_repo.update.assert_awaited_once_with(mock_listing) # Save was attempted