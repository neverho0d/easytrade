# src/marketplace_aggregator/services/listing_service.py

from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

from marketplace_aggregator.models.listing import Listing
from marketplace_aggregator.models.product import Sellable
from marketplace_aggregator.models.promotional_rule import ProductTypeEnum, PromotionalRule
from marketplace_aggregator.models.variable_product import VariableProduct
from marketplace_aggregator.repositories.assembly_repo import AssemblyRepository
from marketplace_aggregator.repositories.inventory_product_repo import InventoryProductRepository
from marketplace_aggregator.repositories.promotional_rule_repo import PromotionalRuleRepository
from marketplace_aggregator.repositories.service_product_repo import ServiceProductRepository
from marketplace_aggregator.repositories.variable_product_repo import VariableProductRepository

# Use relative imports for interfaces and models
from ..repositories.listing_repo import ListingRepository
from ..adapters.marketplace import Marketplace, ListingError


class ListingService:
    """
    Service responsible for managing product listings across marketplaces.
    """

    def __init__(
        self,
        promotional_rule_repo: PromotionalRuleRepository,
        inventory_product_repo: InventoryProductRepository,
        variable_product_repo: VariableProductRepository,
        assembly_repo: AssemblyRepository,
        service_product_repo: ServiceProductRepository,
        listing_repo: ListingRepository,
        marketplace_adapters: Dict[str, Marketplace],  # Inject dependencies
    ):
        """
        Initializes the service with necessary dependencies.

        Args:
            promotional_rule_repo: Repository for accessing promotional rule data.
            inventory_product_repo: Repository for accessing inventory product data.
            variable_product_repo: Repository for accessing variable product data.
            assembly_repo: Repository for accessing assembly data.
            service_product_repo: Repository for accessing service product data.
            listing_repo: Repository for accessing listing data.
            marketplace_adapters: A dictionary mapping marketplace names (str)
                                  to configured Marketplace adapter instances.
        """
        self._promotional_rule_repo = promotional_rule_repo
        self._inventory_product_repo = inventory_product_repo
        self._variable_product_repo = variable_product_repo
        self._assembly_repo = assembly_repo
        self._service_product_repo = service_product_repo
        self._listing_repo = listing_repo
        self._marketplace_adapters = marketplace_adapters
        print("ListingService initialized.")


    async def _get_product_data_and_rule(
        self,
        rule_id: int,
    ) -> Optional[Tuple[Sellable | VariableProduct, PromotionalRule]]:
        # Get the rule
        rule = await self._promotional_rule_repo.get(rule_id)
        if not rule:
            print(f"Service ERROR: Promotional rule with identifier '{rule_id}' not found.")
            return None
        if not rule.is_active:
            print(f"Service INFO: Rule {rule_id} is not active.")
            return None
        
        # Get the product data by querying a proper repository based on the rule.product_type
        product_data: Optional[Sellable | VariableProduct] = None
        try:
            match rule.product_type:
                case ProductTypeEnum.INVENTORY:
                    product_data = await self._inventory_product_repo.get_by_sku(rule.product_identifier)
                case ProductTypeEnum.SERVICE:
                    product_data = await self._service_product_repo.get_by_sku(rule.product_identifier)
                case ProductTypeEnum.VARIABLE:
                    product_data = await self._variable_product_repo.get_by_group_id(rule.product_identifier)
                case ProductTypeEnum.ASSEMBLY:
                    product_data = await self._assembly_repo.get_by_sku(rule.product_identifier)
                case _:
                    print(f"Service ERROR: Unsupported product type '{rule.product_type}' for rule '{rule_id}'.")
                    return None
        except Exception as e:
            print(f"Service ERROR: During product lookup for rule {rule_id}, identifier '{rule.product_identifier}'. Error: {e}")
            return None
        if not product_data:
            print(f"Service ERROR: Product with identifier '{rule.product_identifier}' not found.")
            return None
        
        return product_data, rule

    async def list_item_on_marketplace(
        self,
        rule_id: int
    ) -> Optional[str]:

        # 1. Get Product Data and Marketplace Name
        product_rule_tuple = await self._get_product_data_and_rule(rule_id)
        if not product_rule_tuple:
            return None
        product_data, rule = product_rule_tuple
        marketplace_name = rule.marketplace_name
        print(f"\nService: Attempting async listing for '{product_data}' on '{marketplace_name}'...")

        # 2. Get Adapter (Stays the same logic, but adapter methods are now async)
        adapter = self._marketplace_adapters.get(marketplace_name)
        if not adapter:
             print(f"Service ERROR: Marketplace adapter '{marketplace_name}' not configured.")
             return None

        # 3. Submit Listing (Now awaits adapter call and repo call)
        # Prepare Listing Config
        listing_config = rule.marketplace_specific_settings or {}
        try:
            print(f"Service: Submitting {product_data.__class__.__name__} '{product_data.title}' via {adapter.name} adapter...")
            listing_id_on_marketplace = await adapter.submit_listing(
                product_data,
                listing_config=listing_config
            )
            print(f"Service: Successfully submitted listing. Marketplace Listing ID: {listing_id_on_marketplace}")

            try:
                print(f"Service: Saving internal listing record...")
                new_listing = Listing(
                    rule_id=rule.id,
                    marketplace_name=adapter.name, # Use adapter name
                    marketplace_listing_id=listing_id_on_marketplace,
                    status="active",
                    listed_price=rule.price_override or product_data.get_price(),
                    last_updated_at=datetime.now(timezone.utc)
                )
                await self._listing_repo.add(new_listing) # await repo call (use add)
                print(f"Service: Internal listing record saved.")
            except Exception as repo_err:
                print(f"Service CRITICAL ERROR: Failed to save listing record... Error: {repo_err}")

            return listing_id_on_marketplace

        except ListingError as e:
            print(f"Service ERROR: Failed to submit listing... Error: {e}")
            return None
        except Exception as e:
            print(f"Service CRITICAL ERROR during listing submission: {e}")
            return None


    async def update_price_on_marketplace( # Add async
        self, listing_id: str, marketplace_name: str, sku: str, new_price: float
    ) -> bool:
        print(f"\nService: Attempting async price update...")
        adapter = self._marketplace_adapters.get(marketplace_name)
        if not adapter:
             print(f"Service ERROR: Marketplace adapter '{marketplace_name}' not configured.")
             return False
        try:
            print(f"Service: Updating price via {adapter.name} adapter...")
            await adapter.update_listing_price(listing_id, sku, new_price) # await adapter call
            print(f"Service: Successfully submitted price update for listing '{listing_id}', SKU '{sku}'.")
            # Optional: await self._listing_repo.update(...) here
            return True
        except ListingError as e:
            print(f"Service ERROR: Failed price update... Error: {e}")
            return False
        except Exception as e:
            print(f"Service CRITICAL ERROR during price update: {e}")
            return False


    async def update_stock_on_marketplace( # Add async
        self, listing_id: str, marketplace_name: str, sku_stock: Dict[str, int]
    ) -> bool:
        print(f"\nService: Attempting async stock update...")
        adapter = self._marketplace_adapters.get(marketplace_name)
        if not adapter:
             print(f"Service ERROR: Marketplace adapter '{marketplace_name}' not configured.")
             return False
        try:
            print(f"Service: Updating stock via {adapter.name} adapter...")
            await adapter.update_listing_stock(listing_id, sku_stock) # await adapter call
            print(f"Service: Successfully submitted stock update for listing '{listing_id}'.")
            # Optional: Update internal stock representation or Listing metadata later
            return True
        except ListingError as e:
            print(f"Service ERROR: Failed stock update... Error: {e}")
            return False
        except Exception as e:
            print(f"Service CRITICAL ERROR during stock update: {e}")
            return False
        

# --- Example Usage (Conceptual - how you might wire it up) ---
if __name__ == "__main__" and False:
    from ..repositories.product_repo import InMemoryProductRepository
    from ..repositories.listing_repo import InMemoryListingRepository
    from ..adapters.mock_marketplace import MockMarketplace
    from ..models.product import InventoryProduct  # For adding test data

    print("--- Setting up dependencies ---")
    # 1. Create repository and add some data
    product_repo = InMemoryProductRepository()
    product_repo.add(
        InventoryProduct(sku="TEST-SKU-01", title="Test Widget", price=10.0)
    )
    product_repo.add(
        InventoryProduct(sku="TEST-SKU-02", title="Another Widget", price=15.0)
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

if __name__ == "__main__":  # pragma: no cover
    # --- Imports needed for demonstration ---
    from ..repositories.product_repo import InMemoryProductRepository
    from ..repositories.listing_repo import (
        InMemoryListingRepository,
    )  # Import listing repo

    # Import the concrete adapter, NOT the mock
    from ..adapters.fakeamazon_adapter import FakemazonAdapter
    from ..models.product import InventoryProduct
    from ..models.variable_product import (
        VariableProductBuilder,
    )  # Need builder to create variable product

    print("--- Setting up dependencies for integration run ---")
    # 1. Create repositories
    product_repo = InMemoryProductRepository()
    listing_repo = InMemoryListingRepository()  # Create listing repo instance

    # 2. Add some data using the Builder for a VariableProduct
    builder = VariableProductBuilder(group_id="TUMBLER-G1", title="Insulated Tumbler")
    tumbler_group = (
        builder.set_description("Keeps drinks cold or hot.")
        .add_shared_image("tumbler_lifestyle.jpg")
        .add_inventory_variant(
            sku="TUMBLER-BL-L",
            title="Tumbler (Blue, L)",
            price=25.00,
            attributes={"Color": "Blue", "Size": "Large"},
            weight_kg=0.45,
        )
        .add_inventory_variant(
            sku="TUMBLER-BK-M",
            title="Tumbler (Black, M)",
            price=25.00,
            attributes={"Color": "Black", "Size": "Medium"},
            weight_kg=0.40,
        )
        .build()
    )
    product_repo.add(tumbler_group)  # Add the group to repo

    # Add a simple product too
    widget = InventoryProduct(sku="WIDGET-01", title="Standard Widget", price=9.99)
    product_repo.add(widget)

    # 3. Create and configure the *concrete* marketplace adapter
    fakemazon_config = {"seller_id": "SELLER_AMA_1", "api_key": "AMAZON_FAKE_KEY"}
    fakemazon_adapter = FakemazonAdapter(fakemazon_config)

    marketplace_adapters = {
        fakemazon_adapter.name: fakemazon_adapter
        # Could add other adapters here later
    }

    # 4. Inject dependencies into the service
    listing_service = ListingService(product_repo, listing_repo, marketplace_adapters)

    print("\n--- Running Service Logic with FakemazonAdapter ---")

    # --- List the Variable Product ---
    print("\n>>> Listing Variable Product...")
    listing_id_tumbler = listing_service.list_item_on_marketplace(
        product_identifier="TUMBLER-G1",  # Use group ID
        marketplace_name="Fakemazon",
    )
    print(f"<<< Tumbler Group Listing ID: {listing_id_tumbler}")

    # --- List the Simple Product ---
    print("\n>>> Listing Simple Product...")
    listing_id_widget = listing_service.list_item_on_marketplace(
        product_identifier="WIDGET-01",  # Use SKU
        marketplace_name="Fakemazon",
    )
    print(f"<<< Widget Listing ID: {listing_id_widget}")

    # --- Update Price (if listing succeeded) ---
    if listing_id_tumbler:
        print("\n>>> Updating Price for a Variant...")
        success = listing_service.update_price_on_marketplace(
            listing_id=listing_id_tumbler,
            marketplace_name="Fakemazon",
            sku="TUMBLER-BK-M",  # SKU of the specific variant
            new_price=24.50,
        )
        print(f"<<< Price Update Success: {success}")

    # --- Update Stock (if listing succeeded) ---
    if listing_id_tumbler:
        print("\n>>> Updating Stock for Variants...")
        success = listing_service.update_stock_on_marketplace(
            listing_id=listing_id_tumbler,
            marketplace_name="Fakemazon",
            sku_stock={"TUMBLER-BL-L": 50, "TUMBLER-BK-M": 35},
        )
        print(f"<<< Stock Update Success: {success}")
