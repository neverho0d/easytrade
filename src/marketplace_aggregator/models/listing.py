# src/marketplace_aggregator/models/listing.py

from dataclasses import dataclass, field
from datetime import datetime, timezone  # Use timezone for UTC
from typing import Optional


@dataclass
class Listing:
    """
    Represents a product listing on a specific marketplace,
    using a standardized internal model.
    """

    # --- Identifiers ---
    product_identifier: str  # Our internal SKU or group_id
    marketplace_name: str  # The name of the marketplace adapter used
    marketplace_listing_id: str  # The ID assigned by the marketplace

    # --- Common Listing Data ---
    listing_url: Optional[str] = None
    status: str = "unknown"  # e.g., "active", "inactive", "pending", "error", "ended"
    listed_price: Optional[float] = None  # Last known price pushed or pulled

    # --- Timestamps ---
    # Default to current UTC time
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    # --- Optional Metadata ---
    # For any extra marketplace-specific info we might need to cache
    # metadata: Dict[str, Any] = field(default_factory=dict)

    # Ensure primary identification is clear
    def __post_init__(self):
        if (
            not self.product_identifier
            or not self.marketplace_name
            or not self.marketplace_listing_id
        ):
            raise ValueError("Core listing identifiers cannot be empty")

    # Unique key for storage within a specific marketplace context
    @property
    def composite_id(self) -> tuple[str, str]:
        return (self.marketplace_name, self.marketplace_listing_id)
