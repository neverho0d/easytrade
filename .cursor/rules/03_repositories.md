path: src/marketplace_aggregator/repositories/

# Context for the Repositories Package

Implements the Repository Pattern using Advanced Alchemy.

- Concrete repositories inherit `advanced_alchemy.repository.SQLAlchemyAsyncRepository[ModelType]`.
- Provides async data access (CRUD + custom methods like `get_by_sku`).
- Uses `AsyncSession` injected via DI (typically managed by Litestar plugin).
- Includes `MarketplaceUnitOfWork` for managing atomic transactions in the service layer.
    