# src/marketplace_aggregator/services/listing_service.py

from datetime import datetime, timezone
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from marketplace_aggregator.models.dto import AssemblyListingData, VariableListingData
from marketplace_aggregator.models.listing import Listing, ListingStateError
from marketplace_aggregator.models.product import (
    ComponentInfo,
    Sellable,
    ProductTypeEnum,
)
from marketplace_aggregator.models.promotional_rule import PromotionalRule
from marketplace_aggregator.repositories.assembly_repo import AssemblyRepository
from marketplace_aggregator.repositories.inventory_product_repo import (
    InventoryProductRepository,
)
from marketplace_aggregator.repositories.promotional_rule_repo import (
    PromotionalRuleRepository,
)
from marketplace_aggregator.repositories.service_product_repo import (
    ServiceProductRepository,
)
from marketplace_aggregator.repositories.variable_product_repo import (
    VariableProductRepository,
)
from marketplace_aggregator.services.exceptions import (
    AdapterNotFoundError,
    ListingPreparationError,
    ListingRecordGetError,
    ListingRecordSaveError,
    ProductNotFoundError,
    RuleInactiveError,
    RuleNotFoundError,
)

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
        db_session: AsyncSession,
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
        self._db_session = db_session
        print("ListingService initialized.")

    # --- Helper to get the active rule ---
    async def _get_active_rule(self, rule_id: int) -> PromotionalRule:
        rule = await self._promotional_rule_repo.get(rule_id)
        if not rule:
            raise RuleNotFoundError(rule_id)
        if not rule.is_active:
            raise RuleInactiveError(rule_id)
        return rule

    # --- Helper to find a single Sellable item by SKU and Type ---
    async def _find_sellable_by_sku(self, sku: str, product_type: str) -> Sellable:
        print(f"Service (Internal): Finding Sellable '{sku}' (Type: {product_type})...")
        repo_map = {
            ProductTypeEnum.INVENTORY.value: self._inventory_product_repo,
            ProductTypeEnum.SERVICE.value: self._service_product_repo,
            ProductTypeEnum.ASSEMBLY.value: self._assembly_repo,
        }
        sellable = None
        repo = repo_map.get(product_type)
        if repo and hasattr(repo, "get_by_sku"):
            sellable = await repo.get_by_sku(sku)
        if sellable:
            return sellable
        raise ProductNotFoundError(sku)

    # --- Helper to find multiple Sellable items by SKUs and Type ---
    async def _find_sellables_by_skus(
        self, skus: List[str], product_type: str
    ) -> List[Sellable]:
        print(
            f"Service (Internal): Finding {len(skus)} Sellables (Type: {product_type})..."
        )
        if not skus:
            return []
        repo_map = {
            ProductTypeEnum.INVENTORY.value: self._inventory_product_repo,
            ProductTypeEnum.SERVICE.value: self._service_product_repo,
            ProductTypeEnum.ASSEMBLY.value: self._assembly_repo,
        }
        repo = repo_map.get(product_type)
        if repo and hasattr(repo, "get_by_skus"):
            found_items = await repo.get_by_skus(skus)
            if len(found_items) != len(skus):
                found_skus = {item.get_sku() for item in found_items}
                missing_skus = set(skus) - found_skus
                print(
                    f"Service WARNING: Missing SKUs during bulk fetch: {missing_skus}"
                )
                # Decide: raise error or return partial list? Let's raise for now.
                raise ProductNotFoundError(f"Missing SKUs: {missing_skus}")
            return found_items
        else:
            raise ListingPreparationError(
                f"Cannot bulk fetch for product type '{product_type}'."
            )

    # --- Helper to fetch components for an Assembly ---
    async def _find_components_for_assembly(
        self, component_info: List[ComponentInfo]
    ) -> List[Sellable]:
        print(
            f"Service (Internal): Finding {len(component_info)} assembly components..."
        )
        components = []
        # This could be optimized with fewer DB calls if needed later
        for info in component_info:
            component = await self._find_sellable_by_sku(info["sku"], info["type"])
            if component:
                components.append(component)
        return components

    # --- Helper to prepare the data structure for the adapter ---
    async def _prepare_listing_data(
        self, rule: PromotionalRule
    ) -> Sellable | VariableListingData | AssemblyListingData:
        """Fetches all necessary data based on rule and prepares DTO for adapter."""
        product_identifier = rule.product_identifier
        product_type = rule.product_type

        try:
            if product_type == ProductTypeEnum.VARIABLE.value:
                group = await self._variable_product_repo.get_by_group_id(
                    product_identifier
                )
                if not group:
                    raise ProductNotFoundError(
                        product_identifier
                    )  # Raise if group itself not found
                variants = await self._find_sellables_by_skus(
                    group.get_variant_skus(), group.variant_type
                )
                return VariableListingData(group=group, variants=variants)

            elif product_type == ProductTypeEnum.ASSEMBLY.value:
                assembly = await self._assembly_repo.get_by_sku(product_identifier)
                if not assembly:
                    raise ProductNotFoundError(product_identifier)
                components = await self._find_components_for_assembly(
                    assembly.get_component_info()
                )
                return AssemblyListingData(assembly=assembly, components=components)

            elif product_type in [
                ProductTypeEnum.INVENTORY.value,
                ProductTypeEnum.SERVICE.value,
            ]:
                # _find_sellable_by_sku raises if not found
                sellable = await self._find_sellable_by_sku(
                    product_identifier, product_type
                )
                return sellable
            else:
                raise ListingPreparationError(
                    f"Unknown product type '{product_type}' in rule {rule.id}"
                )
        except ProductNotFoundError:  # Re-raise specific errors from helpers
            raise
        except Exception as e:  # Wrap other unexpected errors during preparation
            raise ListingPreparationError(
                f"Failed preparing data for rule {rule.id}: {e}"
            ) from e

    def _get_adapter(self, marketplace_name: str) -> Marketplace:
        """Gets the configured adapter or raises AdapterNotFoundError."""
        print(f"Service: Getting adapter for marketplace {marketplace_name}...")
        print(f"Service: Available adapters: {self._marketplace_adapters}")
        adapter = self._marketplace_adapters.get(marketplace_name)
        if not adapter:
            raise AdapterNotFoundError(marketplace_name)
        return adapter

    async def _save_listing_record(
        self,
        rule: PromotionalRule,
        product_data: Sellable | VariableListingData | AssemblyListingData,
        marketplace_listing_id: str,
        adapter_name: str,
    ) -> Listing:
        """Creates and saves the internal Listing record."""
        rule_id_val = rule.id
        product_identifier_val = rule.product_identifier
        price_override_val = rule.price_override
        try:
            print(f"Service: Saving internal listing record for rule {rule_id_val}...")
            # Determine price (use override or fetch from product data)
            price_to_store = price_override_val
            if price_to_store is None:
                if isinstance(product_data, Sellable):
                    price_to_store = product_data.get_price()
                elif isinstance(product_data, VariableListingData):
                    # Price of first variant? Or None?
                    price_to_store = (
                        product_data.variants[0].get_price()
                        if product_data.variants
                        else None
                    )
                elif isinstance(product_data, AssemblyListingData):
                    price_to_store = (
                        product_data.assembly.get_price()
                    )  # Placeholder - needs service logic
                else:
                    price_to_store = None  # Fallback

            new_listing = Listing(
                rule_id=rule_id_val,
                product_identifier=product_identifier_val,
                marketplace_name=adapter_name,
                marketplace_listing_id=marketplace_listing_id,
                status="active",  # Default status on successful creation
                listed_price=price_to_store,
                last_updated_at=datetime.now(timezone.utc),
            )
            print(f"Service: Internal listing record to save: {new_listing}")
            await self._listing_repo.add(new_listing)
            print(f"Service: Internal listing record saved for rule {rule_id_val}.")
            return new_listing
        except Exception as repo_err:
            # Wrap repo error in our custom exception
            print(
                f"Service CRITICAL ERROR: Failed to save listing record for rule {rule_id_val}. Error: {repo_err}"
            )
            raise ListingRecordSaveError(
                listing_id=marketplace_listing_id, original_exception=repo_err
            )

    # --- REFACTORED Main Service Method ---
    async def list_item_on_marketplace(self, rule_id: int) -> Optional[str]:
        """
        Processes a PromotionalRule to submit a listing, using centralized error handling.
        """
        print(f"\nService: Processing listing submission for rule ID '{rule_id}'...")
        listing_id_on_marketplace: Optional[str] = None  # Define before try

        print(f"Service: DB Session info: {self._db_session.info}")

        async with self._db_session.begin():
            try:
                # Step 1: Get Rule (raises RuleNotFound / RuleInactive)
                rule = await self._get_active_rule(rule_id)
                print(
                    f"Service: Found active rule for Product '{rule.product_identifier}' on '{rule.marketplace_name}'"
                )

                # Step 2: Get Adapter (raises AdapterNotFound)
                adapter = self._get_adapter(rule.marketplace_name)

                # Step 3: Prepare Data (raises ProductNotFound / ListingPreparationError)
                data_to_submit = await self._prepare_listing_data(rule)
                print(
                    f"Service: Prepared data of type '{data_to_submit.__class__.__name__}' for adapter."
                )

                # Step 4: Prepare Config (simple dict access) just make sure it's not None
                # the actual logic to apply overrides is on the adapter level
                listing_config = rule.marketplace_specific_settings or {}

                # Step 5: Submit Listing (raises ListingError / other Exceptions)
                print(f"Service: Submitting item via {adapter.name} adapter...")
                listing_id_on_marketplace = await adapter.submit_listing(
                    data_to_submit, listing_config=listing_config
                )
                print(
                    f"Service: Successfully submitted listing. Marketplace Listing ID: {listing_id_on_marketplace}"
                )

                # Step 6: Save Listing Record (raises ListingRecordSaveError)
                await self._save_listing_record(
                    rule, data_to_submit, listing_id_on_marketplace, adapter.name
                )

                # If all steps succeeded:
                return listing_id_on_marketplace

            except (
                RuleNotFoundError,
                RuleInactiveError,
                ProductNotFoundError,
                AdapterNotFoundError,
                ListingPreparationError,
            ) as e:
                # Expected errors during setup/data fetching
                print(f"Service INFO: Listing aborted for rule {rule_id}. Reason: {e}")
                return None
            except ListingError as e:
                # Expected errors reported by the marketplace adapter
                print(
                    f"Service ERROR: Marketplace submission failed for rule {rule_id}. Adapter Error: {e}"
                )
                # Optionally: Mark rule as failed? Report error on listing state?
                return None
            except ListingRecordSaveError as e:
                # Critical error: Listing created externally, but couldn't save state internally
                print(
                    f"Service CRITICAL: Listing submitted ({e.listing_id}) but failed internal save! Rule {rule_id}. Error: {e.original_exception}"
                )
                # Decide what to return: the external ID (caller might try to reconcile?), or None?
                # Returning None might be safer if internal state is crucial.
                return None  # Changed from returning ID
            except Exception as e:
                # Catch any other unexpected errors
                print(
                    f"Service CRITICAL: Unexpected error processing rule {rule_id}. Error: {e}"
                )
                # Consider logging traceback here
                import traceback

                traceback.print_exc()
                return None

    async def _get_listing_record(
        self, marketplace_name: str, listing_id: str
    ) -> Listing:
        """Retrieves a Listing record by its ID."""
        listing = await self._listing_repo.get_by_composite_id(
            marketplace_name, listing_id
        )
        if listing:
            return listing
        raise ListingRecordGetError(listing_id)

    async def update_price_on_marketplace(  # Add async
        self, listing_id: str, marketplace_name: str, sku: str, new_price: float
    ) -> bool:
        print("\nService: Attempting price update...")
        async with self._db_session.begin():
            try:
                listing = await self._get_listing_record(marketplace_name, listing_id)
                print(
                    f"Service: Found listing: {listing}, current status: {listing.current_status}"
                )
                listing.update_price(new_price)
                adapter = self._get_adapter(listing.marketplace_name)
                print(f"Service: Updating price via {adapter.name} adapter...")
                await adapter.update_listing_price(
                    listing_id, sku, new_price
                )  # await adapter call
                await self._listing_repo.update(listing)
            except ListingRecordGetError as e:
                print(
                    f"Service ERROR: Failed to get listing record for {listing_id}. Error: {e}"
                )
                return False
            except ListingStateError as e:
                print(f"Service ERROR: Failed to update listing price... Error: {e}")
                return False
            except AdapterNotFoundError as e:
                print(
                    f"Service ERROR: Marketplace adapter '{marketplace_name}' not configured. Error: {e}"
                )
                return False
            except ListingRecordSaveError as e:
                print(
                    f"Service CRITICAL: Listing submitted ({e.listing_id}) but failed internal save! Error: {e.original_exception}"
                )
                # Decide what to return: the external ID (caller might try to reconcile?), or None?
                # Returning None might be safer if internal state is crucial.
                return False
            except Exception as e:
                print(f"Service CRITICAL ERROR during price update: {e}")
                return False
            return True

    async def update_stock_on_marketplace(
        self, listing_id: str, marketplace_name: str, sku_stock: Dict[str, int]
    ) -> bool:
        print("\nService: Attempting stock update...")
        async with self._db_session.begin():
            try:
                listing = await self._get_listing_record(marketplace_name, listing_id)
                print(
                    f"Service: Found listing: {listing}, current status: {listing.current_status}"
                )
                listing.update_stock(sku_stock)
                adapter = self._get_adapter(listing.marketplace_name)
                print(f"Service: Updating stock via {adapter.name} adapter...")
                await adapter.update_listing_stock(
                    listing_id, sku_stock
                )  # await adapter call
                await self._listing_repo.update(listing)
            except ListingRecordGetError as e:
                print(
                    f"Service ERROR: Failed to get listing record for {listing_id}. Error: {e}"
                )
                return False
            except ListingStateError as e:
                print(f"Service ERROR: Failed to update listing stock... Error: {e}")
                return False
            except AdapterNotFoundError as e:
                print(
                    f"Service ERROR: Marketplace adapter '{marketplace_name}' not configured. Error: {e}"
                )
                return False
            except ListingRecordSaveError as e:
                print(
                    f"Service CRITICAL: Listing submitted ({e.listing_id}) but failed internal save! Error: {e.original_exception}"
                )
                # Decide what to return: the external ID (caller might try to reconcile?), or None?
                # Returning None might be safer if internal state is crucial.
                return False
            except Exception as e:
                print(f"Service CRITICAL ERROR during stock update: {e}")
                return False
            return True
