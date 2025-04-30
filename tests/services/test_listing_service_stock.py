# test_listing_service_stock.py

from unittest.mock import AsyncMock, MagicMock
import pytest
from src.marketplace_aggregator.services.listing_service import ListingService
from src.marketplace_aggregator.models.listing import Listing

pytestmark = pytest.mark.asyncio


async def test_update_stock_success(
    listing_service: ListingService,
    mock_listing_repo: MagicMock,
    mock_marketplace_adapter: MagicMock,
    mocker
):
    """Test successful stock update when state allows it."""
    # Arrange
    rule_id = 1
    m_name = mock_marketplace_adapter.name
    l_id = "LIST-1"
    sku = "SKU1"
    sku_stock = {"SKU1": 10, "SKU2": 20}

    # Mock the Listing object returned by the repo
    # Using a real object initialized to 'active' state
    mock_listing = Listing(
        id=1,
        rule_id=rule_id,
        product_identifier=sku,
        marketplace_name=m_name,
        marketplace_listing_id=l_id,
        status="active"
    )
    mock_listing.model_post_init(None)

    # Configure repo mocks
    mock_listing_repo.get_by_composite_id = AsyncMock(return_value=mock_listing)
    mock_listing_repo.update = AsyncMock(return_value=mock_listing)

    # Configure adapter mock for success
    mock_marketplace_adapter.update_listing_stock = AsyncMock(return_value=None)

    # Spy on the listing's state method to ensure it was called
    spy_listing_update_stock = mocker.spy(mock_listing._state, "update_stock")

    # Act
    success = await listing_service.update_stock_on_marketplace(l_id, m_name, sku_stock)

    # Assert
    assert success is True
    mock_listing_repo.get_by_composite_id.assert_awaited_once_with(m_name, l_id)
    spy_listing_update_stock.assert_called_once_with(sku_stock)
    mock_marketplace_adapter.update_listing_stock.assert_awaited_once_with(l_id, sku_stock)
    mock_listing_repo.update.assert_awaited_once_with(mock_listing)
    # assert mock_listing.stock == sku_stock # Verify internal state change


async def test_update_stock_listing_not_found(
    listing_service: ListingService,
    mock_listing_repo: MagicMock,
    mock_marketplace_adapter: MagicMock
):
    pass


async def test_update_stock_state_disallows(
    listing_service: ListingService,
    mock_listing_repo: MagicMock,
    mock_marketplace_adapter: MagicMock
):
    pass


async def test_update_stock_adapter_not_found(
    listing_service: ListingService,
    mock_listing_repo: MagicMock,
    mock_marketplace_adapter: MagicMock
):
    pass


async def test_update_stock_adapter_listing_error(
    listing_service: ListingService,
    mock_listing_repo: MagicMock,
    mock_marketplace_adapter: MagicMock
):
    pass


async def test_update_stock_repo_update_fails(
    listing_service: ListingService,
    mock_listing_repo: MagicMock,
    mock_marketplace_adapter: MagicMock
):
    pass