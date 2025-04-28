# src/marketplace_aggregator/models/product.py

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import List, Optional, TypeAlias
from typing_extensions import TypedDict

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

# Optional: Define helper aliases
Dimensions: TypeAlias = tuple[float, float, float]  # L, W, H
VariantAttributes: TypeAlias = dict[str, str]  # e.g., {"Size": "L", "Color": "Red"}
VariantMap: TypeAlias = dict[str, float]  # e.g., {"Size=L,Color=Red": price_adjustment}


class ProductTypeEnum(StrEnum):
    INVENTORY = "inventory"
    SERVICE = "service"
    ASSEMBLY = "assembly"
    VARIABLE = "variable"


# --- 1. Sellable Interface (using ABC) ---
class Sellable(ABC):
    """
    Abstract Base Class defining the contract for any sellable item
    in the system (individual products, services, assemblies).
    """

    # We make sku and name abstract properties - subclasses must provide them
    @abstractmethod
    def get_sku(self) -> str:
        """The unique Stock Keeping Unit."""
        pass

    @abstractmethod
    def get_title(self) -> str:
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

    @abstractmethod
    def get_type(self) -> ProductTypeEnum:
        """Get the type of the product."""
        pass

    # Maybe add more common methods later, like get_weight, get_type etc.


# Test interface conformity
def process_sellable(item: Sellable):
    print(
        f"Processing {item.__class__.__name__}: {item.get_title()} ({item.get_sku()}) - ${item.get_price():.2f}"
    )


# --- 2. Concrete Leaf: Inventory Product ---
# Represents a specific, trackable product variant
class InventoryProduct(SQLModel, Sellable, table=True):
    """A specific, physical product variant with inventory."""

    id: Optional[int] = Field(default=None, primary_key=True)
    sku: str = Field(unique=True, index=True)
    title: str = Field(index=True)
    price: float = Field(ge=0.0)
    attributes: Optional[VariantAttributes] = Field(
        default=None, sa_column=Column(JSONB)
    )
    description: Optional[str] = Field(default=None)
    images: Optional[List[str]] = Field(default=None, sa_column=Column(JSONB))
    weight_kg: Optional[float] = Field(default=None)
    dimensions_cm: Optional[Dimensions] = Field(default=None, sa_column=Column(JSONB))

    # --- Implement Sellable interface ---

    def get_sku(self) -> str:
        return self.sku

    def get_title(self) -> str:
        return self.title

    def get_price(self) -> float:
        return self.price

    def get_description(self) -> str | None:
        return self.description  # Accessing dataclass field directly

    def get_images(self) -> list[str]:
        return self.images or []  # Accessing dataclass field directly

    def get_type(self) -> ProductTypeEnum:
        return ProductTypeEnum.INVENTORY

    # InventoryProduct specific methods could go here later


# --- 3. Concrete Leaf: Service Product ---
# Represents a non-physical service
class ServiceProduct(SQLModel, Sellable, table=True):
    """A sellable service."""

    id: Optional[int] = Field(default=None, primary_key=True)
    sku: str = Field(unique=True, index=True)
    title: str = Field(index=True)
    price: float = Field(ge=0.0)  # Could be price per hour, fixed price, etc.
    description: Optional[str] = Field(default=None)
    images: Optional[List[str]] = Field(
        default=None, sa_column=Column(JSONB)
    )  # e.g., promotional images
    duration_hours: Optional[float] = Field(
        default=None
    )  # Example service-specific attribute

    # --- Implement Sellable interface ---

    def get_sku(self) -> str:
        return self.sku

    def get_title(self) -> str:
        return self.title

    def get_price(self) -> float:
        return self.price

    def get_description(self) -> str | None:
        return self.description

    def get_images(self) -> list[str] | None:
        return self.images or []

    def get_type(self) -> ProductTypeEnum:
        return ProductTypeEnum.SERVICE

    # ServiceProduct specific methods could go here later


# --- Define a structure for component info ---
class ComponentInfo(TypedDict):  # Using TypedDict for clarity
    sku: str
    type: str  # e.g., "InventoryProduct" or ProductTypeEnum.INVENTORY.value
    quantity: int


# --- 4. Composite: Assembly ---
class Assembly(SQLModel, Sellable, table=True):
    """
    Represents a product composed of other Sellable items (Composite).
    Implements the Sellable interface itself.
    """

    id: Optional[int] = Field(default=None, primary_key=True)  # Primary Key
    sku: str = Field(unique=True, index=True)
    title: str = Field(index=True)
    description: Optional[str] = Field(default=None)
    images: Optional[List[str]] = Field(default=None, sa_column=Column(JSONB))
    component_info: Optional[List[ComponentInfo]] = Field(
        default=None, sa_column=Column(JSONB)
    )
    # --- Implement Sellable interface for the Assembly itself ---

    def get_sku(self) -> str:
        return self.sku

    def get_title(self) -> str:
        return self.title

    def get_price(self) -> float:
        # Price calculation now requires fetching components based on SKUs.
        # This logic belongs in a Service layer using repositories, not the model.
        # For now, return 0 or perhaps store a pre-calculated price?
        # Let's return 0 and add a TODO.
        print(
            "Warning: Assembly.get_price() needs service layer logic to sum component prices."
        )
        return 0.0  # TODO: Implement price calculation in a service layer

    def get_description(self) -> str | None:
        # Return the assembly's own description
        return self.description

    def get_images(self) -> list[str]:
        # Return the assembly's specific images (representing the assembled product)
        # Could potentially combine child images later if needed, but keep simple for now.
        return self.images or []

    def get_type(self) -> ProductTypeEnum:
        return ProductTypeEnum.ASSEMBLY

        # --- Methods for accessing component info ---

    def get_component_info(self) -> list[ComponentInfo]:
        return self.component_info or []


# --- Example Usage ---
if __name__ == "__main__":
    # Cannot instantiate abstract class:
    # sellable = Sellable() # TypeError

    # Create concrete instances
    variant1 = InventoryProduct(
        sku="TS-RD-M",
        title="Cotton T-Shirt (Red, M)",
        price=19.99,
        attributes={"Color": "Red", "Size": "M"},
        weight_kg=0.2,
    )

    service1 = ServiceProduct(
        sku="SVC-SETUP-01",
        title="Basic Setup Service",
        price=99.00,
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

    # print("\n--- Creating Assembly ---")
    # # Create some components (could be InventoryProduct, ServiceProduct, or other Assemblies)
    # desk_legs = InventoryProduct(
    #     sku="LEG-STL-4", title="Steel Legs (Set of 4)", price=40.00
    # )
    # desk_top_oak = InventoryProduct(
    #     sku="TOP-OAK-120", title="Oak Desktop (120cm)", price=75.00
    # )
    # assembly_service = ServiceProduct(
    #     sku="SVC-ASM-DESK", title="Desk Assembly Service", price=50.00
    # )

    # # Create the main assembly product
    # oak_desk_assembly = Assembly(
    #     sku="DESK-OAK-STD",
    #     title="Standard Oak Desk",
    #     description="A sturdy desk with an oak top and steel legs.",
    #     images=["oak_desk_main.jpg"],
    # )

    # # Add components to the assembly
    # oak_desk_assembly.add_component(desk_legs)
    # oak_desk_assembly.add_component(desk_top_oak)
    # oak_desk_assembly.add_component(assembly_service)  # Include service as part!

    # print("\n--- Displaying Assembly Structure ---")
    # oak_desk_assembly.display_structure()

    # print("\n--- Getting Assembly Details via Sellable Interface ---")
    # print(f"SKU: {oak_desk_assembly.sku}")
    # print(f"Title: {oak_desk_assembly.title}")
    # print(f"Description: {oak_desk_assembly.get_description()}")
    # print(f"Images: {oak_desk_assembly.get_images()}")
    # print(f"Total Price (sum of components): ${oak_desk_assembly.get_price():.2f}")

    # # Demonstrate treating assembly just like any other Sellable
    # print("\n--- Processing Assembly via Sellable interface ---")
    # process_sellable(oak_desk_assembly)
