from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
from dataclasses import dataclass, field

from ..adapters.marketplace import ListingError, Marketplace
from ..models.product import Sellable
from ..models.variable_product import VariableProduct


@dataclass
class MockListingItem:
    listing_id: str
    item: Sellable | VariableProduct
    stock: Dict[str, int] = field(default_factory=dict)
    price_overrides: Dict[str, float] = field(default_factory=dict)


class MockMarketplace(Marketplace):
    """
    Mock Marketplace implementation for testing and development.
    """

    _NAME = "MocketPlace"

    def __init__(self, seller_id: str, config: Optional[Dict[str, Any]] = None):
        self._seller_id = seller_id
        self._config = config or {}
        self._listings: Dict[str, MockListingItem] = {}
        self._orders: Dict[str, Dict[str, Any]] = {}
        print(f"Initialized MockMarketplace for seller '{self._seller_id}'")

    @property
    def name(self) -> str:
        """
        The name of the marketplace.
        """
        return self._NAME

    def submit_listing(self, item: Sellable | VariableProduct) -> str:
        """
        Simulates submitting a listing. Generates a fake ID.
        Initial stock is assumed to be empty or needs separate update.
        """
        identifier = item.sku if isinstance(item, Sellable) else item.group_id
        print(
            f"{self.name} ({self._seller_id}): Received submit_listing for {identifier}"
        )

        # generate a random listing id
        listing_id = f"MOCK_{identifier}_{uuid.uuid4().hex[:6]}"

        # Create the mock listing item (stock starts empty)
        mock_item = MockListingItem(listing_id=listing_id, item=item)
        self._listings[listing_id] = mock_item

        print(
            f"{self.name} ({self._seller_id}): Created listing {listing_id} for {identifier}"
        )
        return listing_id

    def update_listing_price(self, listing_id: str, sku: str, new_price: float) -> None:
        """Simulates updating a price. Just prints for the mock."""
        print(f"{self.name} ({self._seller_id}): Received update_listing_price")

        if listing_id not in self._listings:
            print(f"{self.name} ERROR: Listing {listing_id} not found.")
            raise ListingError(f"Listing {listing_id} not found")

        listing = self._listings[listing_id]
        item = listing.item
        # Validate SKU exists for the item
        sku_exists = False
        if isinstance(item, VariableProduct):
            if sku in item.variants:
                sku_exists = True
        elif isinstance(item, Sellable):
            if item.sku == sku:
                sku_exists = True

        if not sku_exists:
            print(f"{self.name} ERROR: SKU {sku} not found in listing {listing_id}.")
            raise ListingError(f"SKU {sku} not found in listing {listing_id}")

        # --- Simple Mock Behavior: Just print ---
        print(
            f"{self.name} ({self._seller_id}): Simulating price update for listing '{listing_id}', SKU '{sku}' to {new_price:.2f}"
        )
        # Optional: Store override price in mock_listing.price_overrides[sku] = new_price
        listing.price_overrides[sku] = new_price

    def update_listing_stock(self, listing_id: str, sku_stock: Dict[str, int]) -> None:
        """Simulates updating stock levels stored within the mock listing."""
        print(
            f"MockPlace ({self._seller_id}): Received update_listing_stock for {listing_id}"
        )
        if listing_id not in self._listings:
            print(f"MockPlace ERROR: Listing {listing_id} not found.")
            raise ListingError(f"Listing {listing_id} not found")

        mock_listing = self._listings[listing_id]
        item = mock_listing.item

        print(
            f"MockPlace ({self._seller_id}): Updating stock for listing '{listing_id}': {sku_stock}"
        )
        for sku, stock in sku_stock.items():
            # Basic validation: does this SKU belong to this listing?
            sku_exists = False
            if isinstance(item, VariableProduct):
                if sku in item.variants:
                    sku_exists = True
            elif isinstance(item, Sellable):
                if item.sku == sku:
                    sku_exists = True

            if not sku_exists:
                print(
                    f"{self.name} WARNING: SKU {sku} not found in listing {listing_id} during stock update."
                )
                ListingError(f"SKU {sku} not found in listing {listing_id}")

            mock_listing.stock[sku] = max(0, stock)  # Update stock in the mock's state

    def get_orders(self, since: datetime) -> List[Dict[str, Any]]:
        """Simulates fetching orders. Returns an empty list for the mock."""
        print(
            f"MockPlace ({self._seller_id}): Received get_orders since {since.isoformat()}"
        )
        # In a real mock, you could add mock orders to self._orders and filter by date
        return []
