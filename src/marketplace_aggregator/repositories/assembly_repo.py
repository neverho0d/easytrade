from typing import List, Optional

from advanced_alchemy.repository import SQLAlchemyAsyncRepository
from advanced_alchemy.filters import CollectionFilter
from ..models.product import Assembly


class AssemblyRepository(SQLAlchemyAsyncRepository[Assembly]):  # type: ignore[type-var]
    """Repository for Assembly data."""

    model_type = Assembly
    # Add custom query methods here later if needed

    async def get_by_sku(self, sku: str) -> Optional[Assembly]:
        """Get an Assembly by its SKU."""
        return await self.get_one_or_none(sku=sku)

    async def get_by_skus(self, skus: List[str]) -> List[Assembly]:
        """Finds multiple Assemblies by their SKUs."""
        if not skus:
            return []
        return await self.list(CollectionFilter(field_name="sku", values=skus))
