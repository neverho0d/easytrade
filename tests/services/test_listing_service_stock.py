# test_listing_service_stock.py

import pytest
from unittest.mock import AsyncMock, MagicMock

from marketplace_aggregator.adapters.marketplace import ListingError
from marketplace_aggregator.models.listing import Listing
from marketplace_aggregator.services.listing_service import ListingService


@pytest.mark.asyncio
async def test_update_stock_success(
    listing_service: ListingService,
    mock_listing_repo: MagicMock,
    mock_marketplace_adapter: MagicMock,
):
    """Test successful stock update call."""
    # Arrange
    rule_id = 1
    listing_id = "MOCK-LISTING-123"
    marketplace_name = mock_marketplace_adapter.name
    sku = "TEST-SKU-01"
    stock_update = {sku: 10}

    # Mock the listing object that the repo will return
    # Important: Create a REAL Listing instance if possible, or a MagicMock that behaves like one
    mock_listing = Listing(  # Using real object simplifies mocking its methods
        product_identifier=sku,
        marketplace_name=marketplace_name,
        marketplace_listing_id=listing_id,
        rule_id=rule_id,
        id=1,
        status="active",
    )

    mock_listing_repo.get_by_composite_id = AsyncMock(return_value=mock_listing)
    mock_marketplace_adapter.update_listing_price = AsyncMock(
        return_value=None
    )  # Success = no exception
    mock_listing_repo.update = AsyncMock(
        return_value=mock_listing
    )  # Simulate successful save

    # Act
    success = await listing_service.update_stock_on_marketplace(
        listing_id=listing_id,
        marketplace_name=marketplace_name,
        sku_stock=stock_update,
    )

    # Assert
    # 1. Check return value is True
    assert success is True

    mock_listing_repo.get_by_composite_id.assert_awaited_once_with(
        marketplace_name, listing_id
    )
    # 2. Verify the adapter's update_listing_stock method was called correctly
    mock_marketplace_adapter.update_listing_stock.assert_awaited_once_with(
        listing_id, stock_update
    )
    mock_listing_repo.update.assert_awaited_once_with(mock_listing)


@pytest.mark.asyncio
async def test_update_stock_listing_not_found(
    listing_service, mock_listing_repo, mock_marketplace_adapter
):
    """Test stock update when listing is not found in repo."""
    # Arrange
    listing_id = "MOCK-LISTING-123"
    marketplace_name = mock_marketplace_adapter.name
    sku = "TEST-SKU-01"
    stock_update = {sku: 10}
    mock_listing_repo.get_by_composite_id = AsyncMock(
        return_value=None
    )  # Simulate not found

    # Act
    success = await listing_service.update_stock_on_marketplace(
        listing_id, marketplace_name, sku_stock=stock_update
    )

    # Assert
    assert success is False
    mock_listing_repo.get_by_composite_id.assert_awaited_once_with(
        marketplace_name, listing_id
    )
    mock_marketplace_adapter.update_listing_stock.assert_not_awaited()
    mock_listing_repo.update.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_stock_state_error(
    listing_service, mock_listing_repo, mock_marketplace_adapter, mocker
):
    """Test stock update when the listing's state disallows it."""
    # Arrange
    rule_id = 1
    marketplace_name = mock_marketplace_adapter.name
    listing_id = "MOCK-LISTING-123"
    sku = "TEST-SKU-01"
    stock_update = {sku: 10}
    # Create a real listing object (e.g., in 'pending' state where update is disallowed)
    mock_listing = Listing(
        product_identifier=sku,
        marketplace_name=marketplace_name,
        marketplace_listing_id=listing_id,
        rule_id=rule_id,
        id=1,
        status="pending",
    )
    # We need __post_init__ to run to set the state object
    mock_listing.model_post_init(None)  # Manually trigger post init for test object

    mock_listing_repo.get_by_composite_id = AsyncMock(return_value=mock_listing)

    # Spy on the state method to ensure it was called (optional but good)
    spy_state_update = mocker.spy(
        mock_listing._state, "update_stock"
    )  # Requires state object access

    # Act
    success = await listing_service.update_stock_on_marketplace(
        listing_id=listing_id,
        marketplace_name=marketplace_name,
        sku_stock=stock_update,
    )

    # Assert
    assert success is False  # Should fail because PendingState disallows price update
    mock_listing_repo.get_by_composite_id.assert_awaited_once_with(
        marketplace_name, listing_id
    )
    spy_state_update.assert_called_once_with(
        stock_update
    )  # Verify state method was called
    mock_marketplace_adapter.update_listing_stock.assert_not_awaited()  # Adapter not called
    mock_listing_repo.update.assert_not_awaited()  # Repo not updated


@pytest.mark.asyncio
async def test_update_stock_adapter_error(
    listing_service, mock_listing_repo, mock_marketplace_adapter
):
    """Test stock update when the adapter call fails."""
    # Arrange
    rule_id = 1
    marketplace_name = mock_marketplace_adapter.name
    listing_id = "MOCK-LISTING-123"
    sku = "TEST-SKU-01"
    stock_update = {sku: 10}
    mock_listing = Listing(
        product_identifier=sku,
        marketplace_name=marketplace_name,
        marketplace_listing_id=listing_id,
        rule_id=rule_id,
        id=1,
        status="active",
    )
    mock_listing.model_post_init(None)  # Ensure state object is created

    mock_listing_repo.get_by_composite_id = AsyncMock(return_value=mock_listing)
    # Configure adapter to raise error
    mock_marketplace_adapter.update_listing_stock = AsyncMock(
        side_effect=ListingError("API stock update failed")
    )
    mock_listing_repo.update = AsyncMock()  # Mock update to check it's not called

    # Act
    success = await listing_service.update_stock_on_marketplace(
        listing_id=listing_id,
        marketplace_name=marketplace_name,
        sku_stock=stock_update,
    )

    # Assert
    assert success is False
    mock_listing_repo.get_by_composite_id.assert_awaited_once_with(
        marketplace_name, listing_id
    )
    mock_marketplace_adapter.update_listing_stock.assert_awaited_once_with(
        listing_id, stock_update
    )
    mock_listing_repo.update.assert_not_awaited()  # Should not save if adapter failed


@pytest.mark.asyncio
async def test_update_stock_repo_update_fails(
    listing_service, mock_listing_repo, mock_marketplace_adapter
):
    """Test stock update success in adapter but failure saving to repo."""
    # Arrange
    rule_id = 1
    marketplace_name = mock_marketplace_adapter.name
    listing_id = "MOCK-LISTING-123"
    sku = "TEST-SKU-01"
    stock_update = {sku: 10}
    mock_listing = Listing(
        product_identifier=sku,
        marketplace_name=marketplace_name,
        marketplace_listing_id=listing_id,
        rule_id=rule_id,
        id=1,
        status="active",
    )
    mock_listing.model_post_init(None)

    mock_listing_repo.get_by_composite_id = AsyncMock(return_value=mock_listing)
    mock_marketplace_adapter.update_listing_stock = AsyncMock(
        return_value=None
    )  # Adapter succeeds
    # Configure repo update to fail
    mock_listing_repo.update = AsyncMock(side_effect=RuntimeError("DB save failed"))

    # Act
    success = await listing_service.update_stock_on_marketplace(
        listing_id=listing_id,
        marketplace_name=marketplace_name,
        sku_stock=stock_update,
    )

    # Assert
    assert success is False  # Fails because repo save failed
    mock_listing_repo.get_by_composite_id.assert_awaited_once_with(
        marketplace_name, listing_id
    )
    mock_marketplace_adapter.update_listing_stock.assert_awaited_once_with(
        listing_id, stock_update
    )
    mock_listing_repo.update.assert_awaited_once_with(mock_listing)  # Attempted save
