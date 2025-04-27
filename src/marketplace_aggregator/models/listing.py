# src/marketplace_aggregator/models/listing.py

from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import datetime, timezone  # Use timezone for UTC
from typing import Dict, Optional, Any

from pydantic import PrivateAttr
from sqlmodel import Field, SQLModel


# --- State Interface ---
class ListingState(ABC):
    """
    Abstract base class for all listing states. Defines actions
    that can be performed, whose behavior depends on the state.
    """

    def __init__(self, listing: "Listing"):
        # States hold a reference back to the Context (Listing)
        self._listing = listing
        print(f"  -> Entering state: {self.__class__.__name__}")

    @abstractmethod
    def update_price(self, new_price: float) -> None:
        """Attempt to update the listing price."""
        pass

    @abstractmethod
    def update_stock(self, sku_stock: Dict[str, int]) -> None:
        """Attempt to update the listing stock."""
        pass

    @abstractmethod
    def activate(self) -> None:
        """Attempt to make the listing active."""
        pass

    @abstractmethod
    def deactivate(self) -> None:
        """Attempt to make the listing inactive."""
        pass

    @abstractmethod
    def end_listing(self) -> None:
        """Attempt to end the listing permanently."""
        pass

    @abstractmethod
    def handle_error(self, error_details: str) -> None:
        """Handle an error associated with this listing."""
        pass

    @property
    def name(self) -> str:
        """Return the name of the state."""
        return self.__class__.__name__.lower().replace("state", "")


class PendingState(ListingState):
    """State for listings awaiting initial activation/review."""

    def update_price(self, new_price: float) -> None:
        print(f"  State({self.name}): Cannot update price yet, listing is pending.")

    def update_stock(self, sku_stock: Dict[str, int]) -> None:
        print(f"  State({self.name}): Cannot update stock yet, listing is pending.")

    def activate(self) -> None:
        print(f"  State({self.name}): Activating listing...")
        # Logic to perhaps verify with marketplace... then transition
        self._listing.set_state(ActiveState(self._listing))  # Transition to Active

    def deactivate(self) -> None:
        print(f"  State({self.name}): Cannot deactivate, listing is still pending.")

    def end_listing(self) -> None:
        print(f"  State({self.name}): Ending pending listing.")
        self._listing.set_state(EndedState(self._listing))  # Transition to Ended

    def handle_error(self, error_details: str) -> None:
        print(
            f"  State({self.name}): Error occurred during pending state: {error_details}"
        )
        self._listing.set_state(ErrorState(self._listing))  # Transition to Error


class ActiveState(ListingState):
    """State for listings that are live on the marketplace."""

    def update_price(self, new_price: float) -> None:
        print(f"  State({self.name}): Updating price to {new_price:.2f}.")
        # Here you might trigger the actual call to the Marketplace Adapter
        # e.g., self._listing.get_adapter().update_listing_price(...)
        # For now, just update the listing's internal value
        self._listing.listed_price = new_price
        self._listing.last_updated_at = datetime.now(timezone.utc)
        print(f"  State({self.name}): Price updated internally.")

    def update_stock(self, sku_stock: Dict[str, int]) -> None:
        print(f"  State({self.name}): Updating stock levels.")
        # Logic to trigger adapter stock update...
        print(f"  State({self.name}): Stock update request sent.")
        self._listing.last_updated_at = datetime.now(timezone.utc)

    def activate(self) -> None:
        print(f"  State({self.name}): Listing is already active.")

    def deactivate(self) -> None:
        print(f"  State({self.name}): Deactivating listing...")
        # Logic to tell marketplace to deactivate...
        self._listing.set_state(InactiveState(self._listing))  # Transition to Inactive

    def end_listing(self) -> None:
        print(f"  State({self.name}): Ending active listing.")
        # Logic to tell marketplace to end...
        self._listing.set_state(EndedState(self._listing))  # Transition to Ended

    def handle_error(self, error_details: str) -> None:
        print(f"  State({self.name}): Error occurred while active: {error_details}")
        self._listing.set_state(ErrorState(self._listing))  # Transition to Error


class InactiveState(ListingState):
    """State for listings that are inactive on the marketplace."""

    def update_price(self, new_price: float) -> None:
        print(f"  State({self.name}): Cannot update price, listing is inactive.")

    def update_stock(self, sku_stock: Dict[str, int]) -> None:
        print(f"  State({self.name}): Cannot update stock, listing is inactive.")

    def activate(self) -> None:
        print(f"  State({self.name}): Activating listing...")
        # Logic to tell marketplace to activate...
        self._listing.set_state(ActiveState(self._listing))  # Transition to Active

    def deactivate(self) -> None:
        print(f"  State({self.name}): Listing is already inactive.")

    def end_listing(self) -> None:
        print(f"  State({self.name}): Cannot end, listing is inactive.")

    def handle_error(self, error_details: str) -> None:
        print(f"  State({self.name}): Error occurred while inactive: {error_details}")
        self._listing.set_state(ErrorState(self._listing))  # Transition to Error


class EndedState(ListingState):
    """State for listings that have been ended."""

    def update_price(self, new_price: float) -> None:
        print(f"  State({self.name}): Cannot update price, listing is ended.")

    def update_stock(self, sku_stock: Dict[str, int]) -> None:
        print(f"  State({self.name}): Cannot update stock, listing is ended.")

    def activate(self) -> None:
        print(f"  State({self.name}): Cannot activate, listing is ended.")

    def deactivate(self) -> None:
        print(f"  State({self.name}): Cannot deactivate, listing is ended.")

    def end_listing(self) -> None:
        print(f"  State({self.name}): Listing is already ended.")

    def handle_error(self, error_details: str) -> None:
        print(f"  State({self.name}): Error occurred while ended: {error_details}")
        self._listing.set_state(ErrorState(self._listing))  # Transition to Error


class ErrorState(ListingState):
    """State for listings that have encountered an error."""

    def update_price(self, new_price: float) -> None:
        print(f"  State({self.name}): Cannot update price, listing is in error.")

    def update_stock(self, sku_stock: Dict[str, int]) -> None:
        print(f"  State({self.name}): Cannot update stock, listing is in error.")

    def activate(self) -> None:
        print(f"  State({self.name}): Cannot activate, listing is in error.")

    def deactivate(self) -> None:
        print(f"  State({self.name}): Cannot deactivate, listing is in error.")

    def end_listing(self) -> None:
        print(f"  State({self.name}): Cannot end, listing is in error.")

    def handle_error(self, error_details: str) -> None:
        print(f"  State({self.name}): Error occurred while in error: {error_details}")
        print(f"  State({self.name}): Listing is already in error.")


class Listing(SQLModel, table=True):
    """
    Represents a product listing on a specific marketplace,
    using a standardized internal model.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    # --- Identifiers ---
    product_identifier: str = Field(index=True)
    rule_id: Optional[int] = Field(
        default=None,
        foreign_key="promotionalrule.id", # Assuming table name 'promotionalrule'
        index=True,
        nullable=True # Make it optional in case a listing could exist without a rule? Or make non-nullable? Let's start nullable.
    )
    marketplace_name: str = Field(
        index=True
    )  # The name of the marketplace adapter used
    marketplace_listing_id: str = Field(
        index=True
    )  # The ID assigned by the marketplace

    # --- Common Listing Data ---
    listing_url: Optional[str] = Field(default=None)
    status: str = Field(default="unknown", index=True)
    listed_price: Optional[float] = Field(
        default=None
    )  # Last known price pushed or pulled

    # --- Timestamps ---
    # Default to current UTC time
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    # Internal state object - not mapped to DB, init=False
    _state: ListingState = PrivateAttr(default=None)

    # --- Optional Metadata ---
    # For any extra marketplace-specific info we might need to cache
    # metadata: Dict[str, Any] = field(default_factory=dict)

    # Ensure primary identification is clear
    def model_post_init(self, __context: Any | None):
        # Initialize the state object AFTER the main fields are set.
        # We need to reconstruct the state based on the stored 'status' string.
        state_map: dict[str, type[ListingState]] = {
            "pending": PendingState,
            "active": ActiveState,
            "inactive": InactiveState,
            "ended": EndedState,
            "error": ErrorState,
        }
        # Get the appropriate class from the map, default to ErrorState if status is unknown
        if not self.id:
            self.status = "pending"
        
        state_class = state_map.get(self.status.lower(), ErrorState)
        self._state = state_class(self)  # Pass self (the Listing instance) to the state

        # Ensure core identifiers are set (Moved from original __post_init__)
        if not all(
            [
                self.rule_id,
                self.marketplace_name,
                self.marketplace_listing_id,
            ]
        ):
            raise ValueError("Core listing identifiers cannot be empty")

    @property
    def marketplace_id(self) -> tuple[str, str]:
        """Returns a composite key for the listing."""
        return (self.marketplace_name, self.marketplace_listing_id)

    def set_state(self, new_state: ListingState) -> None:
        """Allows the state objects to change the listing's state."""
        print(
            f"Listing {self.marketplace_listing_id}: Changing state from {self._state.name} to {new_state.name}"
        )
        self._state = new_state
        self.status = new_state.name  # Update the persistent status field
        self.last_updated_at = datetime.now(timezone.utc)

    @property
    def surrent_status(self) -> str:
        """Returns the name of the current state class."""
        # Handle case where _state might not be initialized yet if accessed before __post_init__ somehow
        return self._state.name if self._state else self.status

    # --- Public methods delegate to the current state ---
    def update_price(self, new_price: float) -> None:
        print(
            f"\nListing {self.marketplace_listing_id}: Requesting price update to {new_price:.2f}"
        )
        self._state.update_price(new_price)

    def update_stock(self, sku_stock: Dict[str, int]) -> None:
        print(
            f"\nListing {self.marketplace_listing_id}: Requesting stock update: {sku_stock}"
        )
        self._state.update_stock(sku_stock)

    def activate(self) -> None:
        print(f"\nListing {self.marketplace_listing_id}: Requesting activation...")
        self._state.activate()

    def deactivate(self) -> None:
        print(f"\nListing {self.marketplace_listing_id}: Requesting deactivation...")
        self._state.deactivate()

    def end_listing(self) -> None:
        print(f"\nListing {self.marketplace_listing_id}: Requesting ending...")
        self._state.end_listing()

    def report_error(self, error_details: str) -> None:
        print(
            f"\nListing {self.marketplace_listing_id}: Reporting error: {error_details}"
        )
        self._state.handle_error(error_details)


if __name__ == "__main__":
    listing = Listing(
        rule_id="1234567890",
        marketplace_name="Amazon",
        marketplace_listing_id="1234567890",
    )
    print(f"Listing {listing.marketplace_listing_id} is in state: {listing.status}")
    listing.update_price(100.00)
    print(f"Listing {listing.marketplace_listing_id} is in state: {listing.status}")
    listing.activate()
    listing.update_price(100.00)
    print(f"Listing {listing.marketplace_listing_id} is in state: {listing.status}")
    listing.deactivate()
    listing.update_price(100.00)
    print(f"Listing {listing.marketplace_listing_id} is in state: {listing.status}")
    listing.end_listing()
    listing.update_price(100.00)
    print(f"Listing {listing.marketplace_listing_id} is in state: {listing.status}")
    listing.report_error("Test error")
    listing.update_price(100.00)
    print(f"Listing {listing.marketplace_listing_id} is in state: {listing.status}")
    listing.activate()
    listing.update_price(100.00)
    print(f"Listing {listing.marketplace_listing_id} is in state: {listing.status}")
