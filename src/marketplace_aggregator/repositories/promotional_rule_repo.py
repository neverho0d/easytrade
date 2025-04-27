# src/marketplace_aggregator/repositories/promotional_rule_repo.py

from typing import List, Optional
from advanced_alchemy.repository import SQLAlchemyAsyncRepository

# Use relative imports
from ..models.promotional_rule import PromotionalRule


class PromotionalRuleRepository(SQLAlchemyAsyncRepository[PromotionalRule]):
    """Repository for PromotionalRule data."""

    model_type = PromotionalRule

    # --- Add custom query methods as needed ---

    async def find_active_rules_by_product(
        self, product_identifier: str
    ) -> List[PromotionalRule]:
        """Find all active rules for a given product identifier."""
        return await self.list(product_identifier=product_identifier, is_active=True)

    async def find_active_rule_for_marketplace(
        self, product_identifier: str, marketplace_name: str
    ) -> Optional[PromotionalRule]:
        """Find the specific active rule for a product on a marketplace."""
        return await self.get_one_or_none(
            product_identifier=product_identifier,
            marketplace_name=marketplace_name,
            is_active=True,
        )

    # Add other specific finders later (e.g., list all active rules)
