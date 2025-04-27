# src/marketplace_aggregator/adapters/fakeamazon_adapter.py

import asyncio
from typing import Dict, Any, List, Optional, TypedDict
from datetime import datetime
import uuid
import time  # For potential simulation

# Use relative imports
from .marketplace import Marketplace, ListingError
from ..models.product import Sellable, InventoryProduct
from ..models.variable_product import VariableProduct


class FakemazonVariant(TypedDict, total=False):
    sku: str
    price: float
    attributes: dict[str, str]
    images: list[str] | None
    ean: str
    weight_kg: float | None
    stock: int | None


class FakemazonApiPayload(TypedDict, total=False):
    listing_type: str
    group_id: str
    sku: str
    ean: str
    price: float
    title: str
    description: str | None
    brand: str
    category: str
    images: list[str] | None
    variants: list[FakemazonVariant]
    weight_kg: float | None
    stock: int | None


class FakemazonAdapter(Marketplace):
    """
    Simulated adapter for a specific marketplace ('Fakemazon').
    Focuses on translating internal models to a hypothetical API format.
    """

    _NAME = "Fakemazon"  # Class attribute for the name

    def __init__(self, seller_config: Dict[str, Any]):
        """
        Initialize with seller-specific config (e.g., API keys).
        """
        self._seller_id = seller_config.get("seller_id", "UNKNOWN")
        self._api_key = seller_config.get("api_key", "FAKE_KEY")
        # Simple internal state for the mock
        self._api_listings: Dict[
            str, FakemazonApiPayload
        ] = {}  # Store the "API payload" sent
        print(f"Initialized FakemazonAdapter for seller '{self._seller_id}'")

    @property
    def name(self) -> str:
        return self._NAME

    async def submit_listing(
        self,
        item: Sellable | VariableProduct,
        listing_config: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Translates our internal product model to a fake Amazon API structure
        and 'submits' it (prints and stores locally).
        """
        print(
            f"\nFakemazonAdapter: Preparing listing submission for '{item.title if isinstance(item, Sellable) else item.name}'..."
        )

        api_payload: FakemazonApiPayload
        identifier = ""  # Used for generating listing ID

        # --- TODO: Implement Translation Logic ---
        # Use isinstance() to check the type of 'item'.
        # Based on the type, construct the 'api_payload' dictionary
        # in a format "Fakemazon" might expect.

        if isinstance(item, VariableProduct):
            # Handle VariableProduct - create payload with parent info + variants list
            print("  (Detected VariableProduct - formatting with variants)")
            identifier = item.group_id
            api_payload = {
                "listing_type": "variable",
                "group_id": item.group_id,
                "title": item.name,  # Use group name
                "description": item.get_description(),
                "brand": "Generic Brand",  # Example fixed value
                "category": "Misc",  # Example fixed value
                "images": item.get_shared_images(),
                "variants": [],
            }
            for variant_sku, variant_obj in item.variants.items():
                # Assume variant_obj is InventoryProduct for simplicity here
                # In reality, need to handle different Sellable types if needed
                variant_payload: FakemazonVariant = {
                    "sku": variant_sku,
                    "price": variant_obj.get_price(),
                    "attributes": getattr(
                        variant_obj, "attributes", {}
                    ),  # Safely get attributes
                    "images": variant_obj.get_images(),
                    "ean": f"EAN-{variant_sku}",  # Example generated field
                }
                if isinstance(variant_obj, InventoryProduct):
                    variant_payload["weight_kg"] = variant_obj.weight_kg
                api_payload["variants"].append(variant_payload)

        elif isinstance(item, Sellable):
            # Handle simple Sellable item (InventoryProduct, Service, Assembly)
            print("  (Detected single Sellable item - formatting simple listing)")
            identifier = item.sku
            api_payload = {
                "listing_type": "simple",
                "sku": item.sku,
                "title": item.title,
                "description": item.get_description(),
                "price": item.get_price(),
                "brand": "Generic Brand",
                "category": "Misc",
                "images": item.get_images(),
                "ean": f"EAN-{item.sku}",
            }
            # Add type-specific fields if needed (e.g., weight for Inventory)
            if isinstance(item, InventoryProduct):
                api_payload["weight_kg"] = item.weight_kg

        else:
            print(f"FakemazonAdapter ERROR: Unsupported item type: {type(item)}")
            raise ListingError(f"Cannot list unsupported type {type(item)}")

        # Apply promotional rule if provided
        if listing_config:
            api_payload = self.listing_config(api_payload, listing_config)

        # Simulate API call
        print("FakemazonAdapter: Simulating API call with payload:")
        import json  # Pretty print the dict

        print(json.dumps(api_payload, indent=2))
        await asyncio.sleep(0.5)  # Simulate network delay

        # Generate fake listing ID and store payload for mock verification
        listing_id = f"FKZ-{identifier}-{uuid.uuid4().hex[:4]}"
        self._api_listings[listing_id] = api_payload  # Store what was "sent"

        print(f"FakemazonAdapter: Submission successful. Listing ID: {listing_id}")
        return listing_id

    def listing_config(self, api_payload: FakemazonApiPayload, listing_config: Dict[str, Any]) -> FakemazonApiPayload:
        """
        Apply promotional rule to the API payload.
        """
        for key, value in listing_config.items():
            # if key is the same as in FakemazonApiPayload, update the value
            if key in api_payload:
                api_payload[key] = value
        return api_payload

    # --- Implement other methods (Simplified for Mock) ---

    async def update_listing_price(self, listing_id: str, sku: str, new_price: float) -> None:
        print(
            f"\nFakemazonAdapter: Received update_price for {listing_id}, SKU {sku} to {new_price:.2f}"
        )
        if listing_id not in self._api_listings:
            raise ListingError(f"Listing ID {listing_id} not found on Fakemazon.")
        # In a real scenario, construct API payload and send.
        # Here, we could update self._api_listings[listing_id] if needed for testing.
        print("FakemazonAdapter: Simulating price update call...")
        await asyncio.sleep(0.2)
        # Update the price for the specific SKU in the internal listing state after the acknowledgement
        if "variants" in self._api_listings[listing_id]:
            for variant in self._api_listings[listing_id]["variants"]:
                if variant["sku"] == sku:
                    variant["price"] = new_price
                    break
        else:
            self._api_listings[listing_id]["price"] = new_price
        print(f"FakemazonAdapter: Price update acknowledged for {listing_id}/{sku}.")

    async def update_listing_stock(self, listing_id: str, sku_stock: Dict[str, int]) -> None:
        print(
            f"\nFakemazonAdapter: Received update_stock for {listing_id}: {sku_stock}"
        )
        if listing_id not in self._api_listings:
            raise ListingError(f"Listing ID {listing_id} not found on Fakemazon.")
        # In a real scenario, construct API payload and send.
        print("FakemazonAdapter: Simulating stock update call...")
        await asyncio.sleep(0.3)
        # Update the stock for the specific SKU in the internal listing state after the acknowledgement
        for sku, stock in sku_stock.items():
            if "variants" in self._api_listings[listing_id]:
                for variant in self._api_listings[listing_id]["variants"]:
                    if variant["sku"] == sku:
                        variant["stock"] = stock
                        break
            else:
                self._api_listings[listing_id]["stock"] = stock
        print(f"FakemazonAdapter: Stock update acknowledged for {listing_id}.")

    async def get_orders(self, since: datetime) -> List[Dict[str, Any]]:
        print(f"\nFakemazonAdapter: Received get_orders since {since.isoformat()}")
        print("FakemazonAdapter: Simulating order fetch call...")
        await asyncio.sleep(0.5)
        print("FakemazonAdapter: Returning empty order list for mock.")
        return []  # Return empty list for simplicity
