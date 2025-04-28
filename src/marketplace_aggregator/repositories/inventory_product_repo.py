from typing import List, Optional

from advanced_alchemy.repository import SQLAlchemyAsyncRepository
from advanced_alchemy.filters import CollectionFilter
from ..models.product import InventoryProduct


class InventoryProductRepository(SQLAlchemyAsyncRepository[InventoryProduct]):  # type: ignore[type-var]
    """Repository for InventoryProduct data."""

    model_type = InventoryProduct
    # Add custom query methods here later if needed

    async def get_by_sku(self, sku: str) -> Optional[InventoryProduct]:
        """Get an InventoryProduct by its SKU."""
        return await self.get_one_or_none(sku=sku)

    async def get_by_skus(self, skus: List[str]) -> List[InventoryProduct]:
        """Finds multiple InventoryProducts by their SKUs."""
        if not skus:
            return []
        return await self.list(CollectionFilter(field_name="sku", values=skus))
