path: src/marketplace_aggregator/models/

# Context for the Models Package

Defines core data structures and domain entities.

- Uses `sqlmodel.SQLModel` with `table=True` for persistent entities.
- Uses standard `dataclasses` or `typing.TypedDict` for DTOs (e.g., `VariableListingData`).
- Uses `abc.ABC` for interfaces (e.g., `Sellable`).
- Models focus on data; complex behavior delegated (e.g., `Listing` uses State pattern via `ListingState`).
- Key models: `Sellable` (interface), `InventoryProduct`, `ServiceProduct`, `Assembly` (implement `Sellable`), `VariableProduct` (groups variants), `PromotionalRule`, `Listing`.
