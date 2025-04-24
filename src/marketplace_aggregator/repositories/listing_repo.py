# src/marketplace_aggregator/repositories/listing_repo.py

from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Optional

# Use relative imports
from ..models.listing import Listing

ListingKey = Tuple[str, str] # Type alias for (marketplace_name, listing_id)

class ListingRepository(ABC):
    """
    Interface defining operations for storing and retrieving Listing data.
    """

    @abstractmethod
    def add_or_update(self, listing: Listing) -> None:
        """Adds a new listing or updates an existing one based on composite key."""
        pass

    @abstractmethod
    def get(self, marketplace_name: str, listing_id: str) -> Optional[Listing]:
        """Retrieves a specific listing by its marketplace and listing ID."""
        pass

    @abstractmethod
    def get_by_product(self, product_identifier: str) -> List[Listing]:
        """Retrieves all listings associated with an internal product identifier."""
        pass

    @abstractmethod
    def list_all(self) -> List[Listing]:
        """Lists all stored listings."""
        pass

    @abstractmethod
    def remove(self, marketplace_name: str, listing_id: str) -> bool:
        """Removes a listing. Returns True if found and removed."""
        pass


# --- In-Memory Implementation ---

class InMemoryListingRepository(ListingRepository):
    """
    An in-memory implementation of the ListingRepository.
    Uses a dictionary keyed by (marketplace_name, marketplace_listing_id).
    """
    def __init__(self):
        # Key: Tuple(marketplace_name, marketplace_listing_id)
        # Value: Listing object
        self._listings: Dict[ListingKey, Listing] = {}
        print("Initialized InMemoryListingRepository")

    def add_or_update(self, listing: Listing) -> None:
        # Use the composite key for storage/update
        key = listing.composite_id
        print(f"Repo: Adding/Updating listing with key '{key}'")
        self._listings[key] = listing


    def get(self, marketplace_name: str, listing_id: str) -> Optional[Listing]:
        # Retrieve by composite key
        key: ListingKey = (marketplace_name, listing_id)
        print(f"Repo: Getting listing with key '{key}'")
        return self._listings.get(key)

    def get_by_product(self, product_identifier: str) -> List[Listing]:
        # Iterate through values to find matches
        print(f"Repo: Getting listings for product identifier '{product_identifier}'")
        return [
            listing for listing in self._listings.values()
            if listing.product_identifier == product_identifier
        ]


    def list_all(self) -> List[Listing]:
        print(f"Repo: Listing all ({len(self._listings)}) listings.")
        return list(self._listings.values())


    def remove(self, marketplace_name: str, listing_id: str) -> bool:
        # Remove item by composite key
        key: ListingKey = (marketplace_name, listing_id)
        print(f"Repo: Attempting to remove listing with key '{key}'")
        if key in self._listings:
            del self._listings[key]
            print(f"Repo: Removed listing '{key}'")
            return True
        else:
            print(f"Repo: Listing '{key}' not found for removal.")
            return False