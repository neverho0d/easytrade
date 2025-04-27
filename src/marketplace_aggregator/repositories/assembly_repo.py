from typing import Optional

from advanced_alchemy.repository import SQLAlchemyAsyncRepository

from ..models.product import Assembly


class AssemblyRepository(SQLAlchemyAsyncRepository[Assembly]):
    """Repository for Assembly data."""

    model_type = Assembly
    # Add custom query methods here later if needed

    async def get_by_sku(self, sku: str) -> Optional[Assembly]:
        """Get an Assembly by its SKU."""
        return await self.get_one_or_none(sku=sku)
