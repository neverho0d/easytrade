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
)
from marketplace_aggregator.models.promotional_rule import ProductTypeEnum


# --- Variable Product Grouping Class ---
# Note: This class ITSELF is likely NOT Sellable
class VariableProduct(SQLModel, table=True):
    """Groups related Sellable variants and holds shared info."""

    id: Optional[int] = Field(default=None, primary_key=True)  # Primary Key
    group_id: str = Field(unique=True, index=True)  # E.g., "TSHIRT-COTTON"
    title: str = Field(index=True)  # E.g., "Cotton T-Shirt" (the shared name)
    variant_type: ProductTypeEnum = Field(index=True)
    description: Optional[str] = Field(default=None)
    shared_images: Optional[List[str]] = Field(default=None, sa_column=Column(JSONB))
    # We use a dictionary mapping variant SKU to the variant Sellable object
    variant_skus: Optional[List[str]] = Field(default=None, sa_column=Column(JSONB))

    # Getters for shared properties
    def get_title(self) -> str:
        return self.title

    @property
    def name(self) -> str:
        return self.title

    def get_price(self) -> float:
        # TODO: Implement price calculation in a service layer
        print(
            "Warning: VariableProduct.get_price() needs service layer logic to average variant prices."
        )
        return 0.0

    def get_description(self) -> str | None:
        return self.description

    def get_shared_images(self) -> list[str]:
        return self.shared_images or []

    def get_variant_skus(self) -> list[str]:
        return self.variant_skus or []


# --- 5. Builder for VariableProduct ---
class VariableProductBuilder:
    def __init__(self, group_id: str, title: str):
        self._variable_product = VariableProduct(group_id=group_id, title=title)
        self._variant_skus_to_add: list[str] = []
        self._variants_to_save: list[Sellable] = []
        self._variant_type: ProductTypeEnum | None = None
        print(
            f"Builder initialized for VariableProduct Group {group_id} ('{title}')..."
        )

    def set_description(self, description: str) -> Self:
        self._variable_product.description = description
        return self

    def add_shared_image(self, image_url: str) -> Self:
        if not self._variable_product.shared_images:
            self._variable_product.shared_images = []
        self._variable_product.shared_images.append(image_url)
        return self

    def add_variant_object(self, variant: Sellable) -> Self:
        if self._variant_type is None:
            self._variant_type = variant.get_type()
        else:
            if self._variant_type != variant.get_type():
                raise ValueError(
                    f"Cannot add variant of type {variant.get_type()} to a VariableProduct of type {self._variant_type}"
                )
        self._variant_skus_to_add.append(variant.get_sku())
        self._variants_to_save.append(variant)
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
        self.add_variant_object(variant)
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
        self.add_variant_object(variant)
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
            variant.component_skus = [
                c.get_sku() for c in components
            ]  # Set SKUs of components
        self.add_variant_object(variant)
        return self

    def build(self) -> VariableProduct:
        print(
            f"--- Building VariableProduct Group: {self._variable_product.group_id} ---"
        )
        if not self._variants_to_save:
            raise ValueError("VariableProduct must have at least one variant.")
        self._variable_product.variant_skus = self._variant_skus_to_add
        # TODO: later, we'll save the variants stored in self._variants_to_save to the database
        return self._variable_product
