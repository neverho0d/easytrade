# Add these dataclasses (not SQLModels)
from dataclasses import dataclass
from typing import List

# Need to import the actual models too
from .product import Sellable, Assembly  # Relative paths might change
from .variable_product import VariableProduct


@dataclass
class VariableListingData:
    """DTO to pass full variable product info to adapters."""

    group: VariableProduct
    variants: List[Sellable]  # The fully loaded variant objects

    def get_title(self) -> str:
        return self.group.get_title()


@dataclass
class AssemblyListingData:
    """DTO to pass full assembly info to adapters."""

    assembly: Assembly
    components: List[Sellable]  # The fully loaded component objects

    def get_title(self) -> str:
        return self.assembly.get_title()
