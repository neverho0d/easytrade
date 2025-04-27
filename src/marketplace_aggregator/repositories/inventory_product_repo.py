from typing import Optional

from advanced_alchemy.repository import SQLAlchemyAsyncRepository

from ..models.product import InventoryProduct


class InventoryProductRepository(SQLAlchemyAsyncRepository[InventoryProduct]):
    """Repository for InventoryProduct data."""
    model_type = InventoryProduct
    # Add custom query methods here later if needed

    async def get_by_sku(self, sku: str) -> Optional[InventoryProduct]:
        """Get an InventoryProduct by its SKU."""
        return await self.get_one_or_none(sku=sku)
