# src/marketplace_aggregator/models/product.py

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, TypeAlias

# Optional: Define helper aliases
Dimensions: TypeAlias = tuple[float, float, float]  # L, W, H
VariantAttributes: TypeAlias = dict[str, str]  # e.g., {"Size": "L", "Color": "Red"}
VariantMap: TypeAlias = dict[str, float]  # e.g., {"Size=L,Color=Red": price_adjustment}


# --- 1. Sellable Interface (using ABC) ---
class Sellable(ABC):
    """
    Abstract Base Class defining the contract for any sellable item
    in the system (individual products, services, assemblies).
    """

    # We make sku and name abstract properties - subclasses must provide them
    @property
    @abstractmethod
    def sku(self) -> str:
        """The unique Stock Keeping Unit."""
        pass

    @property
    @abstractmethod
    def title(self) -> str:
        """The display title of the sellable item."""
        pass

    @abstractmethod
    def get_price(self) -> float:
        """Get the primary price for this sellable item."""
        pass

    @abstractmethod
    def get_description(self) -> str | None:
        """Get the description, if available."""
        pass

    @abstractmethod
    def get_images(self) -> list[str] | None:
        """Get a list of image URLs/paths."""
        pass

    # Maybe add more common methods later, like get_weight, get_type etc.


# Test interface conformity
def process_sellable(item: Sellable):
    print(
        f"Processing {item.__class__.__name__}: {item.title} ({item.sku}) - ${item.get_price():.2f}"
    )


# --- 2. Concrete Leaf: Inventory Product ---
# Represents a specific, trackable product variant
@dataclass
class InventoryProduct(Sellable):
    """A specific, physical product variant with inventory."""

    _sku: str
    _title: str
    _price: float
    attributes: VariantAttributes = field(default_factory=dict)
    description: str | None = None
    images: list[str] = field(default_factory=list)
    weight_kg: float | None = None
    dimensions_cm: Dimensions | None = None

    # --- Implement Sellable interface ---

    @property
    def sku(self) -> str:
        return self._sku

    @property
    def title(self) -> str:
        return self._title

    @property
    def price(self) -> float:
        return self._price

    def get_price(self) -> float:
        return self._price

    def get_description(self) -> str | None:
        return self.description  # Accessing dataclass field directly

    def get_images(self) -> list[str]:
        return self.images  # Accessing dataclass field directly

    # InventoryProduct specific methods could go here later


# --- 3. Concrete Leaf: Service Product ---
# Represents a non-physical service
@dataclass
class ServiceProduct(Sellable):
    """A sellable service."""

    _sku: str
    _title: str
    _price: float  # Could be price per hour, fixed price, etc.
    description: str | None = None
    images: list[str] | None = field(default_factory=list)  # e.g., promotional images
    duration_hours: float | None = None  # Example service-specific attribute

    # --- Implement Sellable interface ---

    @property
    def sku(self) -> str:
        return self._sku

    @property
    def title(self) -> str:
        return self._title

    @property
    def price(self) -> float:
        return self._price

    def get_price(self) -> float:
        return self._price

    def get_description(self) -> str | None:
        return self.description

    def get_images(self) -> list[str] | None:
        return self.images

    # ServiceProduct specific methods could go here later


# --- 4. Composite: Assembly ---
class Assembly(Sellable):
    """
    Represents a product composed of other Sellable items (Composite).
    Implements the Sellable interface itself.
    """

    def __init__(
        self,
        sku: str,
        title: str,
        description: str | None = None,
        images: list[str] | None = None,
    ):
        # Store the Assembly's own details
        self._sku = sku
        self._title = title
        self._description = description
        # Use provided images or default to empty list
        self._images = images if images is not None else []
        # Initialize the list to hold child components
        self._components: List[Sellable] = []
        print(f"Assembly created: {self.title} ({self.sku})")

    # --- Child Management Methods ---
    def add_component(self, component: Sellable) -> None:
        """Adds a child component (part) to the assembly."""
        print(f"  Adding component '{component.title}' to assembly '{self.title}'")
        self._components.append(component)

    def remove_component(self, component: Sellable) -> None:
        """Removes a child component from the assembly."""
        print(
            f"  Attempting to remove component '{component.title}' from assembly '{self.title}'"
        )
        try:
            self._components.remove(component)
            print("  Successfully removed.")
        except ValueError:
            print("  Component not found.")

    # --- Implement Sellable interface for the Assembly itself ---
    @property
    def sku(self) -> str:
        # Return the assembly's own SKU
        return self._sku

    @property
    def title(self) -> str:
        # Return the assembly's own title
        return self._title

    def get_price(self) -> float:
        # Composite logic: Calculate price by summing the prices
        # of all child components recursively.
        # Assembly fee is a ServiceProduct that is added to the list of components, so its price is included.
        return sum(component.get_price() for component in self._components)

    def get_description(self) -> str | None:
        # Return the assembly's own description
        return self._description

    def get_images(self) -> list[str]:
        # Return the assembly's specific images (representing the assembled product)
        # Could potentially combine child images later if needed, but keep simple for now.
        return self._images

    # --- Optional: Composite-specific display method (similar to previous example) ---
    def display_structure(self, indent_level: int = 0) -> None:
        """Displays the assembly and its components recursively."""
        indent = "  " * indent_level
        print(
            f"{indent}* Assembly: {self.title} (SKU: {self.sku}) - Composite Price: ${self.get_price():.2f}"
        )
        for component in self._components:
            # Check if the child component has a 'display_structure' method itself
            if hasattr(component, "display_structure") and callable(
                component.display_structure
            ):
                component.display_structure(indent_level + 1)
            else:
                # If child is a leaf (Product/Service), maybe just print basic info
                indent_child = "  " * (indent_level + 1)
                print(
                    f"{indent_child}- Leaf: {component.title} ({component.sku}) - Price: ${component.get_price():.2f}"
                )


# --- Example Usage ---
if __name__ == "__main__":
    # Cannot instantiate abstract class:
    # sellable = Sellable() # TypeError

    # Create concrete instances
    variant1 = InventoryProduct(
        _sku="TS-RD-M",
        _title="Cotton T-Shirt (Red, M)",
        _price=19.99,
        attributes={"Color": "Red", "Size": "M"},
        weight_kg=0.2,
    )

    service1 = ServiceProduct(
        _sku="SVC-SETUP-01",
        _title="Basic Setup Service",
        _price=99.00,
        description="One hour remote setup assistance.",
        duration_hours=1.0,
    )

    print("--- Created Sellable Items ---")
    print(
        f"Inventory: {variant1.title} ({variant1.sku}), Price: {variant1.get_price()}"
    )
    print(
        f"Service: {service1.title} ({service1.sku}), Price: {service1.get_price()}, Duration: {service1.duration_hours}h"
    )

    print("\n--- Processing via Sellable interface ---")
    process_sellable(variant1)
    process_sellable(service1)

    print("\n--- Creating Assembly ---")
    # Create some components (could be InventoryProduct, ServiceProduct, or other Assemblies)
    desk_legs = InventoryProduct(
        _sku="LEG-STL-4", _title="Steel Legs (Set of 4)", _price=40.00
    )
    desk_top_oak = InventoryProduct(
        _sku="TOP-OAK-120", _title="Oak Desktop (120cm)", _price=75.00
    )
    assembly_service = ServiceProduct(
        _sku="SVC-ASM-DESK", _title="Desk Assembly Service", _price=50.00
    )

    # Create the main assembly product
    oak_desk_assembly = Assembly(
        sku="DESK-OAK-STD",
        title="Standard Oak Desk",
        description="A sturdy desk with an oak top and steel legs.",
        images=["oak_desk_main.jpg"],
    )

    # Add components to the assembly
    oak_desk_assembly.add_component(desk_legs)
    oak_desk_assembly.add_component(desk_top_oak)
    oak_desk_assembly.add_component(assembly_service)  # Include service as part!

    print("\n--- Displaying Assembly Structure ---")
    oak_desk_assembly.display_structure()

    print("\n--- Getting Assembly Details via Sellable Interface ---")
    print(f"SKU: {oak_desk_assembly.sku}")
    print(f"Title: {oak_desk_assembly.title}")
    print(f"Description: {oak_desk_assembly.get_description()}")
    print(f"Images: {oak_desk_assembly.get_images()}")
    print(f"Total Price (sum of components): ${oak_desk_assembly.get_price():.2f}")

    # Demonstrate treating assembly just like any other Sellable
    print("\n--- Processing Assembly via Sellable interface ---")
    process_sellable(oak_desk_assembly)
