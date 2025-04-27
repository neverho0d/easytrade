# src/marketplace_aggregator/models/variable_product.py

from typing import List, Optional, Self

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from marketplace_aggregator.models.product import (
    Assembly,
    InventoryProduct,
    Sellable,
    ServiceProduct,
    VariantAttributes,
    process_sellable,
)


# --- Variable Product Grouping Class ---
# Note: This class ITSELF is likely NOT Sellable
class VariableProduct(SQLModel, table=True):
    """Groups related Sellable variants and holds shared info."""

    id: Optional[int] = Field(default=None, primary_key=True)  # Primary Key
    group_id: str = Field(unique=True, index=True)  # E.g., "TSHIRT-COTTON"
    title: str = Field(index=True)  # E.g., "Cotton T-Shirt" (the shared name)
    description: Optional[str] = Field(default=None)
    shared_images: Optional[List[str]] = Field(default=None, sa_column=Column(JSONB))
    # We use a dictionary mapping variant SKU to the variant Sellable object
    variant_skus: Optional[List[str]] = Field(default=None, sa_column=Column(JSONB))

    # def add_variant(self, variant: Sellable):
    #     """Adds a fully defined Sellable variant to the group."""
    #     if not variant.sku:
    #         raise ValueError("Variant must have an SKU.")
    #     if variant.sku in self.variants:
    #         print(f"Warning: Variant SKU {variant.sku} already exists. Overwriting.")
    #     print(f"  -> Adding variant SKU {variant.sku} to group {self.group_id}")
    #     self.variants[variant.sku] = variant

    # def get_variant_by_sku(self, sku: str) -> Sellable | None:
    #     """Retrieves a specific variant by its unique SKU."""
    #     return self.variants.get(sku)

    # def get_variants_by_attributes(
    #     self, attrs_to_match: VariantAttributes
    # ) -> list[Sellable]:
    #     """Finds variants matching specific attributes."""
    #     # Assumes variants are InventoryProduct or similar with 'attributes' field
    #     matches = []
    #     for variant in self.variants.values():
    #         if hasattr(variant, "attributes") and isinstance(variant.attributes, dict):
    #             # Check if all requested attributes match the variant's attributes
    #             if all(
    #                 variant.attributes.get(k) == v for k, v in attrs_to_match.items()
    #             ):
    #                 matches.append(variant)
    #     return matches

    # Getters for shared properties
    def get_title(self) -> str:
        return self.title

    @property
    def name(self) -> str:
        return self.title

    def get_description(self) -> str | None:
        return self.description

    def get_shared_images(self) -> list[str]:
        return self.shared_images

    def get_variant_skus(self) -> list[str]:
        return self.variant_skus


# --- 5. Builder for VariableProduct ---
class VariableProductBuilder:
    def __init__(self, group_id: str, title: str):
        self._variable_product = VariableProduct(group_id=group_id, title=title)
        print(
            f"Builder initialized for VariableProduct Group {group_id} ('{title}')..."
        )

    def set_description(self, description: str) -> Self:
        self._variable_product.description = description
        return self

    def add_shared_image(self, image_url: str) -> Self:
        self._variable_product.shared_images.append(image_url)
        return self

    def add_variant_object(self, variant: Sellable) -> Self:
        self._variable_product.add_variant(variant)
        return self

    def add_inventory_variant(
        self,
        sku: str,
        title: str,
        price: float,
        attributes: VariantAttributes,
        weight_kg: float | None = None,
    ) -> Self:
        variant = InventoryProduct(
            sku=sku,
            title=title,
            price=price,
            attributes=attributes,
            weight_kg=weight_kg,
        )
        self._variable_product.add_variant(variant)
        return self

    def add_service_variant(
        self,
        sku: str,
        title: str,
        price: float,
        description: str | None = None,
        images: list[str] | None = None,
        duration_hours: float | None = None,
    ) -> Self:
        variant = ServiceProduct(
            sku=sku,
            title=title,
            price=price,
            description=description,
            images=images,
            duration_hours=duration_hours,
        )
        self._variable_product.add_variant(variant)
        return self

    def add_assembly_variant(
        self,
        sku: str,
        title: str,
        description: str | None = None,
        images: list[str] | None = None,
        components: list[Sellable] | None = None,
    ) -> Self:
        variant = Assembly(
            sku=sku,
            title=title,
            description=description,
            images=images,
        )
        if components:
            print(f"    -> Adding {len(components)} components to assembly {sku}")
            for component in components:
                variant.add_component(component)
        self._variable_product.add_variant(variant)
        return self

    def build(self) -> VariableProduct:
        print(
            f"--- Building VariableProduct Group: {self._variable_product.group_id} ---"
        )
        if not self._variable_product.variants:
            raise ValueError("VariableProduct must have at least one variant.")
        return self._variable_product


# --- Example Usage ---
if __name__ == "__main__":
    print("\n--- Building Variable Product ---")
    builder = VariableProductBuilder(group_id="TSHIRT-CTN", title="Cotton T-Shirt")

    variable_product = (
        builder.set_description("Soft and comfortable cotton.")
        .add_shared_image("tshirt_model.jpg")
        .add_inventory_variant(  # Use convenience method
            sku="TS-CTN-RD-M",
            title="Cotton T-Shirt (Red, M)",
            price=19.99,
            attributes={"Color": "Red", "Size": "M"},
            weight_kg=0.18,
        )
        .add_inventory_variant(
            sku="TS-CTN-RD-L",
            title="Cotton T-Shirt (Red, L)",
            price=19.99,
            attributes={"Color": "Red", "Size": "L"},
            weight_kg=0.20,
        )
        .add_inventory_variant(
            sku="TS-CTN-BL-M",
            title="Cotton T-Shirt (Blue, M)",
            price=20.50,
            attributes={"Color": "Blue", "Size": "M"},
            weight_kg=0.18,
        )
        .build()
    )

    print("\n--- Built Variable Product ---")
    print(variable_product)

    print("\n--- Finding Variants ---")
    red_medium_variant = variable_product.get_variant_by_sku("TS-CTN-RD-M")
    print(f"Found by SKU: {red_medium_variant}")

    blue_variants = variable_product.get_variants_by_attributes({"Color": "Blue"})
    print(f"Found Blue variants: {blue_variants}")

    large_variants = variable_product.get_variants_by_attributes({"Size": "L"})
    print(f"Found Large variants: {large_variants}")

    # Process a specific variant using Sellable interface
    if red_medium_variant:
        print("\n--- Processing a specific variant ---")
        process_sellable(red_medium_variant)  # Requires process_sellable definition
