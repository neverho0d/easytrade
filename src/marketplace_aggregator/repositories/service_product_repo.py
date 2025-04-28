from typing import List, Optional

from advanced_alchemy.repository import SQLAlchemyAsyncRepository
from advanced_alchemy.filters import CollectionFilter
from ..models.product import ServiceProduct


class ServiceProductRepository(SQLAlchemyAsyncRepository[ServiceProduct]):  # type: ignore[type-var]
    """Repository for ServiceProduct data."""

    model_type = ServiceProduct

    async def get_by_sku(self, sku: str) -> Optional[ServiceProduct]:
        """Get a ServiceProduct by its SKU."""
        return await self.get_one_or_none(sku=sku)

    async def get_by_skus(self, skus: List[str]) -> List[ServiceProduct]:
        """Finds multiple ServiceProducts by their SKUs."""
        if not skus:
            return []
        return await self.list(CollectionFilter(field_name="sku", values=skus))
