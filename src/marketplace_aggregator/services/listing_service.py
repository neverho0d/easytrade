# src/marketplace_aggregator/services/listing_service.py

from datetime import datetime, timezone
from typing import Dict, Optional

from marketplace_aggregator.models.listing import Listing

# Use relative imports for interfaces and models
from ..repositories.product_repo import (
    ProductRepository,
)  # Import alias too
from ..repositories.listing_repo import ListingRepository
from ..adapters.marketplace import Marketplace, ListingError


class ListingService:
    """
    Service responsible for managing product listings across marketplaces.
    """

    def __init__(
        self,
        product_repo: ProductRepository,
        listing_repo: ListingRepository,
        marketplace_adapters: Dict[str, Marketplace],  # Inject dependencies
    ):
        """
        Initializes the service with necessary dependencies.

        Args:
            product_repo: Repository for accessing product data.
            marketplace_adapters: A dictionary mapping marketplace names (str)
                                  to configured Marketplace adapter instances.
        """
        self._product_repo = product_repo
        self._listing_repo = listing_repo
        self._marketplace_adapters = marketplace_adapters
        print("ListingService initialized.")

    def list_item_on_marketplace(
        self,
        product_identifier: str,  # SKU or group_id
        marketplace_name: str,
    ) -> Optional[str]:
        """
        Fetches a product/group and submits it as a listing to a specific marketplace.

        Args:
            product_identifier: The SKU or group_id of the product/group to list.
            marketplace_name: The name of the target marketplace (must match a key
                              in the injected marketplace_adapters).

        Returns:
            The new marketplace listing ID if successful, None otherwise.
        """
        print(
            f"\nService: Attempting to list '{product_identifier}' on '{marketplace_name}'..."
        )

        # 1. Get the specific Marketplace adapter instance
        # Implement:
        #   - Get adapter from self._marketplace_adapters using marketplace_name
        #   - Handle case where marketplace_name is not found (print error, return None)

        adapter = self._marketplace_adapters.get(marketplace_name)
        if not adapter:
            print(
                f"Service ERROR: Marketplace adapter for '{marketplace_name}' not configured."
            )
            return None

        # 2. Get the product data from the repository
        # Implement:
        #   - Get product_data from self._product_repo using product_identifier
        #   - Handle case where product_identifier is not found (print error, return None)
        product_data = self._product_repo.get(product_identifier)
        if not product_data:
            print(
                f"Service ERROR: Product/Group with identifier '{product_identifier}' not found."
            )
            return None

        # 3. Submit the listing via the adapter
        # Implement:
        #   - Call adapter.submit_listing(product_data)
        #   - Use a try...except ListingError block to handle potential submission errors
        #   - Print success/error messages
        #   - Return the listing_id on success, None on error
        try:
            print(
                f"Service: Submitting {product_data.__class__.__name__} '{product_identifier}' via {adapter.name} adapter..."
            )
            # Note: We are currently NOT passing seller_config here, as the adapter
            # was initialized with it. This might need revisiting depending on how
            # multi-tenant the adapters are designed. For now, assume adapter is pre-configured.
            listing_id_on_marketplace = adapter.submit_listing(product_data)
            print(
                f"Service: Successfully submitted listing. Marketplace Listing ID: {listing_id_on_marketplace}"
            )

            try:
                print("Service: Saving internal listing record...")
                new_listing = Listing(
                    product_identifier=product_identifier,
                    marketplace_name=marketplace_name,  # Or adapter.name
                    marketplace_listing_id=listing_id_on_marketplace,
                    status="active",  # Assume active on successful submission
                    # Optionally get price/URL if adapter returns more details
                    # listed_price=product_data.get_price(), # Example
                    last_updated_at=datetime.now(timezone.utc),
                )
                self._listing_repo.add_or_update(new_listing)
                print("Service: Internal listing record saved.")
            except Exception as repo_err:
                # Log or handle failure to save internal listing record - crucial!
                print(
                    f"Service CRITICAL ERROR: Failed to save listing record for {listing_id_on_marketplace} after successful submission! Error: {repo_err}"
                )
                # Decide recovery strategy: maybe try deleting listing from marketplace?
                # For now, we still return the ID, but flag the error.

            return listing_id_on_marketplace
        except ListingError as e:
            print(
                f"Service ERROR: Failed to submit listing for '{product_identifier}' on '{marketplace_name}'. Error: {e}"
            )
            return None
        except Exception as e:  # Catch unexpected errors too
            print(f"Service CRITICAL ERROR during listing submission: {e}")
            # Potentially re-raise or log more details
            return None

    def update_price_on_marketplace(
        self, listing_id: str, marketplace_name: str, sku: str, new_price: float
    ) -> bool:
        """
        Updates the price for a specific SKU within a listing on a marketplace.
        Args:
            listing_id: The ID of the listing to update.
            marketplace_name: The name of the marketplace to update.
            sku: The SKU of the product to update.
            new_price: The new price to set.
        Returns:
            True if the update was likely successful, False otherwise.
        """
        print(
            f"\nService: Attempting price update for listing '{listing_id}', SKU '{sku}' on '{marketplace_name}' to {new_price:.2f}"
        )

        # 1. Get adapter instance from self._marketplace_adapters
        #    - Handle case where marketplace_name is not found (print error, return False)
        adapter = self._marketplace_adapters.get(marketplace_name)
        if not adapter:
            print(
                f"Service ERROR: Marketplace adapter for '{marketplace_name}' not configured."
            )
            return False

        # 2. Call adapter.update_listing_price(...)
        #    - Wrap in try...except ListingError (and maybe Exception)
        #    - Print success or error messages
        #    - Return True on success, False on error
        try:
            print(
                f"Service: Updating price for listing '{listing_id}' on '{marketplace_name}' to {new_price:.2f}"
            )
            adapter.update_listing_price(listing_id, sku, new_price)
            print(
                f"Service: Successfully updated price for listing '{listing_id}' on '{marketplace_name}' to {new_price:.2f}"
            )
            return True
        except ListingError as e:
            print(
                f"Service ERROR: Failed to update price for listing '{listing_id}' on '{marketplace_name}'. Error: {e}"
            )
            return False
        except Exception as e:
            # Catch unexpected errors from the adapter for more robustness
            print(f"Service CRITICAL ERROR during price update: {e}")
            # import traceback; traceback.print_exc() # Consider logging traceback
            return False

    def update_stock_on_marketplace(
        self, listing_id: str, marketplace_name: str, sku_stock: Dict[str, int]
    ) -> bool:
        """
        Updates the stock levels for one or more SKUs within a listing on a marketplace.
        Args:
            listing_id: The ID of the listing to update.
            marketplace_name: The name of the marketplace to update.
            sku_stock: A dictionary mapping SKUs to their new stock levels.
        Returns:
            True if the update was likely successful, False otherwise.
        """
        print(
            f"\nService: Attempting stock update for listing '{listing_id}' on '{marketplace_name}': {sku_stock}"
        )
        # 1. Get adapter instance, return False if not found (print error)
        adapter = self._marketplace_adapters.get(marketplace_name)
        if not adapter:
            print(
                f"Service ERROR: Marketplace adapter for '{marketplace_name}' not configured."
            )
            return False

        # 2. Call adapter.update_listing_stock(...) in try/except ListingError
        #    Print success/error messages
        #    Return True on success, False on error
        try:
            print(f"Service: Updating stock via {adapter.name} adapter...")
            adapter.update_listing_stock(listing_id, sku_stock)
            print(
                f"Service: Successfully updated stock for listing '{listing_id}' on '{marketplace_name}'."
            )
            return True
        except ListingError as e:
            print(
                f"Service ERROR: Failed to update stock for listing '{listing_id}' on '{marketplace_name}'. Error: {e}"
            )
            return False
        except Exception as e:
            # Catch unexpected errors from the adapter for more robustness
            print(f"Service CRITICAL ERROR during stock update: {e}")
            # import traceback; traceback.print_exc() # Consider logging traceback
            return False


# --- Example Usage (Conceptual - how you might wire it up) ---
if __name__ == "__main__":
    from ..repositories.product_repo import InMemoryProductRepository
    from ..repositories.listing_repo import InMemoryListingRepository
    from ..adapters.mock_marketplace import MockMarketplace
    from ..models.product import InventoryProduct  # For adding test data

    print("--- Setting up dependencies ---")
    # 1. Create repository and add some data
    product_repo = InMemoryProductRepository()
    product_repo.add(
        InventoryProduct(_sku="TEST-SKU-01", _title="Test Widget", _price=10.0)
    )
    product_repo.add(
        InventoryProduct(_sku="TEST-SKU-02", _title="Another Widget", _price=15.0)
    )
    listing_repo = InMemoryListingRepository()

    # 2. Create and configure marketplace adapters
    mock_adapter = MockMarketplace(seller_id="SELLER_123")
    # In a real app, you might load configs and create adapters for different marketplaces
    marketplace_adapters: Dict[str, Marketplace] = {
        mock_adapter.name: mock_adapter  # Use adapter's name as key
        # "AmazonUS": AmazonMarketplace(config_for_amazon_us), # Example
    }

    # 3. Inject dependencies into the service
    listing_service = ListingService(product_repo, listing_repo, marketplace_adapters)

    print("\n--- Running Service Logic ---")
    # List item TEST-SKU-01 on MockPlace
    list_id1 = listing_service.list_item_on_marketplace(
        "TEST-SKU-01", mock_adapter.name
    )
    print(f"Resulting Listing ID 1: {list_id1}")

    # List item TEST-SKU-02 on MockPlace
    list_id2 = listing_service.list_item_on_marketplace(
        "TEST-SKU-02", mock_adapter.name
    )
    print(f"Resulting Listing ID 2: {list_id2}")

    # Try listing non-existent item
    list_id3 = listing_service.list_item_on_marketplace("BAD-SKU", mock_adapter.name)
    print(f"Resulting Listing ID 3: {list_id3}")

    # Try listing on non-existent marketplace
    list_id4 = listing_service.list_item_on_marketplace("TEST-SKU-01", "UnknownPlace")
    print(f"Resulting Listing ID 4: {list_id4}")
