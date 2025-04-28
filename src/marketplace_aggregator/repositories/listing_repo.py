# src/marketplace_aggregator/repositories/listing_repo.py

from typing import List, Tuple, Optional

# Import the SQLAlchemy/SQLModel Repository base from Advanced Alchemy
from advanced_alchemy.repository import SQLAlchemyAsyncRepository

# Use relative imports
from ..models.listing import Listing

ListingKey = Tuple[str, str]  # Type alias for (marketplace_name, listing_id)


class ListingRepository(SQLAlchemyAsyncRepository[Listing]):  # type: ignore[type-var]
    """SQLAlchemy/SQLModel implementation for Listing data access using Advanced Alchemy."""

    model_type = Listing  # Link to the SQLModel class

    # --- Implement Interface Methods using Base Repository Features ---

    async def add_or_update(self, data: Listing) -> Listing:
        # AA's add handles session add and assumes commit happens via Unit of Work or caller
        # It usually returns the added instance.
        # Use add_or_update semantics if PK `id` might already exist
        if data.id:
            return await self.update(data)  # Use update if ID exists
        else:
            return await super().add(data)  # Use base add if no ID (new instance)

    async def update(self, data: Listing, *args, **kwargs) -> Listing:
        # Use the base repository's update method
        return await super().update(data, *args, **kwargs)

    async def get_by_composite_id(
        self, marketplace_name: str, marketplace_listing_id: str
    ) -> Optional[Listing]:
        # Use the base repository's get_one_or_none with keyword filters
        return await self.get_one_or_none(
            marketplace_name=marketplace_name,
            marketplace_listing_id=marketplace_listing_id,
        )

    async def get_by_product(self, product_identifier: str) -> List[Listing]:
        # Use the base repository's list method with a keyword filter
        results, _ = await self.list_and_count(product_identifier=product_identifier)
        # list_and_count returns (items, total_count) - we only need items here
        # Or just use list: results = await self.list(product_identifier=product_identifier)
        return results

    async def list_all(self) -> List[Listing]:
        # Use the base repository's list method without filters
        return await self.list()

    async def delete_by_composite_id(
        self, marketplace_name: str, marketplace_listing_id: str
    ) -> Optional[Listing]:
        # 1. Fetch the item by the composite key to get its primary key (id)
        item_to_delete = await self.get_by_composite_id(
            marketplace_name, marketplace_listing_id
        )
        if item_to_delete and item_to_delete.id is not None:
            # 2. Use the base repository's delete method with the primary key
            await super().delete(item_to_delete.id)
            # The base delete usually returns the ID of the deleted item
            # We return the object we found for confirmation.
            return item_to_delete
        return None  # Return None if not found

    # NOTE: The SQLAlchemyAsyncRepository likely requires an AsyncSession
    # to be injected or available when it's instantiated or its methods are called.
    # We will handle this when integrating with Litestar's DI system.
    # For now, we assume the session is implicitly managed by the base class methods
    # (as configured by Advanced Alchemy's setup).
