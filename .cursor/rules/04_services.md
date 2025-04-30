path: src/marketplace_aggregator/services/

# Context for the Services Package

Contains application business logic and use case orchestration.

- Services are asynchronous (`async def`).
- Dependencies (UoW, Adapters) injected via `__init__`.
- Uses `MarketplaceUnitOfWork` (`async with uow:`) for atomic transactions.
- Raises specific custom exceptions from `services.exceptions`.
- Orchestrates calls to repositories (via UoW) and adapters.
- Key services: `ListingService`.
    