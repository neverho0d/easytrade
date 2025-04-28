from typing import Optional

from advanced_alchemy.repository import SQLAlchemyAsyncRepository

from ..models.variable_product import VariableProduct


class VariableProductRepository(SQLAlchemyAsyncRepository[VariableProduct]):  # type: ignore[type-var]
    """Repository for VariableProduct group data."""

    model_type = VariableProduct
    # Add custom query methods here later if needed

    async def get_by_group_id(self, group_id: str) -> Optional[VariableProduct]:
        """Get a VariableProduct by its group_id."""
        return await self.get_one_or_none(group_id=group_id)
