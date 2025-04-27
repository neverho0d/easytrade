from typing import Optional

from advanced_alchemy.repository import SQLAlchemyAsyncRepository

from ..models.product import ServiceProduct


class ServiceProductRepository(SQLAlchemyAsyncRepository[ServiceProduct]):
    """Repository for ServiceProduct data."""
    model_type = ServiceProduct

    async def get_by_sku(self, sku: str) -> Optional[ServiceProduct]:
        """Get a ServiceProduct by its SKU."""
        return await self.get_one_or_none(sku=sku)
