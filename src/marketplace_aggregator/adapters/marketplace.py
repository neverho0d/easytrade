# src/marketplace_aggregator/adapters/marketplace.py

from abc import ABC, abstractmethod
from datetime import datetime
from typing import (
    List,
    Dict,
    Any,
    Optional,
)  # Using Any for now for generic order/config dicts

# Import our core model - use relative import within the package
from ..models.product import Sellable
from ..models.variable_product import VariableProduct


class Marketplace(ABC):
    """
    Abstract Base Class defining the interface for interacting
    with different external marketplaces.
    Concrete implementations will adapt specific marketplace APIs.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Returns the user-friendly name of the marketplace (e.g., 'Amazon US')."""
        pass

    @abstractmethod
    async def submit_listing(
        self,
        item: Sellable | VariableProduct,
        listing_config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Submits a Sellable item as a new listing on the marketplace.

        Args:
            item: The Sellable object (InventoryProduct, ServiceProduct, Assembly) to list.
                  Note: Handling VariableProduct might require listing each variant.
            seller_config: Marketplace-specific configuration for the seller
                           (e.g., API keys, category mappings, return policies).

        Returns:
            The marketplace-specific ID for the newly created listing.

        Raises:
            ListingError: If the submission fails.
        """
        pass

    @abstractmethod
    async def update_listing_price(
        self, listing_id: str, sku: str, new_price: float
    ) -> None:
        """
        Updates the price for a specific SKU within a listing on the marketplace.

        Args:
            listing_id: The marketplace's ID for the listing.
            sku: The specific SKU within the listing to update (for variants).
            new_price: The new price.
            seller_config: Seller-specific configuration/credentials.

        Raises:
            ListingError: If the update fails.
        """
        pass

    @abstractmethod
    async def update_listing_stock(
        self, listing_id: str, sku_stock: Dict[str, int]
    ) -> None:
        """
        Updates the stock levels for one or more SKUs within a listing.

        Args:
            listing_id: The marketplace's ID for the listing.
            sku_stock: A dictionary mapping SKU strings to their new stock level.
            seller_config: Seller-specific configuration/credentials.

        Raises:
            ListingError: If the update fails.
        """
        # Note: We decided stock is handled externally from Sellable model,
        # but the Marketplace *adapter* will need to know how to push stock updates.
        pass

    @abstractmethod
    async def get_orders(self, since: datetime) -> List[Dict[str, Any]]:
        """
        Fetches recent orders from the marketplace since a given time.

        Args:
            since: The datetime object indicating the start time for fetching orders.
            seller_config: Seller-specific configuration/credentials.

        Returns:
            A list of dictionaries, where each dictionary represents an order
            in a common format defined by our system (details TBD).

        Raises:
            OrderError: If fetching orders fails.
        """
        pass


# --- Define custom Exceptions (optional but good practice) ---
class MarketplaceError(Exception):
    """Base exception for marketplace interactions."""

    pass


class ListingError(MarketplaceError):
    """Exception related to listing operations."""

    pass


class OrderError(MarketplaceError):
    """Exception related to order operations."""

    pass
