# src/marketplace_aggregator/models/promotional_rule.py

from enum import StrEnum
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from sqlmodel import SQLModel, Field
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB


class ProductTypeEnum(StrEnum):
    INVENTORY = "inventory"
    SERVICE = "service"
    ASSEMBLY = "assembly"
    VARIABLE = "variable"


class PromotionalRule(SQLModel, table=True):
    """
    Represents a rule/configuration for listing a specific product/group
    on a specific marketplace, potentially with overrides.
    """

    id: Optional[int] = Field(default=None, primary_key=True)

    # Link to internal product/group and target marketplace
    product_identifier: str = Field(index=True, description="Internal SKU or group_id")
    product_type: ProductTypeEnum = Field(
        index=True, description="Type of product/group"
    )
    marketplace_name: str = Field(
        index=True, description="Name matching a configured Marketplace adapter"
    )

    # Rule status
    is_active: bool = Field(
        default=True, index=True, description="Whether this rule should be processed"
    )
    rule_name: Optional[str] = Field(
        default=None, description="User-friendly name for the rule"
    )  # Optional name

    # --- Overrides ---
    price_override: Optional[float] = Field(
        default=None, description="Specific price for this marketplace listing"
    )
    title_override: Optional[str] = Field(
        default=None, description="Specific title for this marketplace listing"
    )
    description_override: Optional[str] = Field(
        default=None, description="Specific description for this marketplace listing"
    )
    # Add other potential overrides (images, etc.) if needed

    # --- Marketplace-Specific Settings ---
    # Using JSONB to store arbitrary key-value settings
    marketplace_specific_settings: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB),
        description="Dict for settings specific to the marketplace (e.g., category ID, auction type)",
    )

    # --- Timestamps ---
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False
    )
    last_updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False
    )
