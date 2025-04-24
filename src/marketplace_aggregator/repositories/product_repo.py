# src/marketplace_aggregator/repositories/product_repo.py

from abc import ABC, abstractmethod
from typing import List, Dict, Optional

# Import our potentially complex model types using relative paths
from ..models.product import Sellable
from ..models.variable_product import VariableProduct

# Define a type alias for the items our repository might store or return
ProductData = Sellable | VariableProduct

class ProductRepository(ABC):
    """
    Interface defining operations for storing and retrieving product data
    (both individual Sellable items and VariableProduct groups).
    """

    @abstractmethod
    def add(self, product_data: ProductData) -> None:
        """Adds or updates a product/group in the repository."""
        pass

    @abstractmethod
    def get(self, identifier: str) -> Optional[ProductData]:
        """
        Retrieves a product/group by its unique identifier
        (SKU for Sellable, group_id for VariableProduct).
        """
        pass

    @abstractmethod
    def list_all(self) -> List[ProductData]:
        """Lists all products/groups in the repository."""
        pass

    @abstractmethod
    def remove(self, identifier: str) -> bool:
        """Removes a product/group by its identifier. Returns True if found and removed."""
        pass


# --- In-Memory Implementation ---

class InMemoryProductRepository(ProductRepository):
    """
    An in-memory implementation of the ProductRepository for development/testing.
    Uses a dictionary for storage.
    """
    def __init__(self):
        # Store items using SKU or group_id as the key
        self._products: Dict[str, ProductData] = {}
        print("Initialized InMemoryProductRepository")

    def add(self, product_data: ProductData) -> None:
        # Determine the key (SKU or group_id)
        identifier = None
        if isinstance(product_data, Sellable):
             identifier = product_data.sku
        elif isinstance(product_data, VariableProduct):
             identifier = product_data.group_id
        else:
             raise TypeError("Unsupported type for repository")

        if not identifier:
             raise ValueError("Product data must have a valid identifier (SKU or group_id)")

        print(f"Repo: Adding/Updating product with ID '{identifier}'")
        self._products[identifier] = product_data


    def get(self, identifier: str) -> Optional[ProductData]:
        # Retrieve by key
        print(f"Repo: Getting product with ID '{identifier}'")
        return self._products.get(identifier)


    def list_all(self) -> List[ProductData]:
        # Return all stored items
        print(f"Repo: Listing all ({len(self._products)}) products.")
        return list(self._products.values())


    def remove(self, identifier: str) -> bool:
        # Remove item by key
        print(f"Repo: Attempting to remove product with ID '{identifier}'")
        if identifier in self._products:
             del self._products[identifier]
             print(f"Repo: Removed product '{identifier}'")
             return True
        else:
             print(f"Repo: Product '{identifier}' not found for removal.")
             return False


# --- Example (Conceptual) Usage in a Service ---
# (We'll build services properly later)
# class ListingService:
#     def __init__(self, product_repo: ProductRepository):
#         self._product_repo = product_repo
#
#     def create_listing_from_id(self, product_id: str, marketplace: Marketplace):
#         product_data = self._product_repo.get(product_id)
#         if product_data:
#             # ... use marketplace.submit_listing ...
#             pass
#         else:
#             print(f"Error: Product {product_id} not found.")