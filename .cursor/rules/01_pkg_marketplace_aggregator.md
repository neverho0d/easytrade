path: src/marketplace_aggregator/

# Context for the marketplace_aggregator Python Package

This package contains the core source code for the application.

Key Architectural Principles:
- Layered Architecture: models, repositories, services, adapters, controllers.
- Asynchronous: Using `asyncio`, `async`/`await`.
- Dependency Injection: Managed by Litestar, configured in `main.py`.
- Repository Pattern: Using Advanced Alchemy's `SQLAlchemyAsyncRepository`.
- Adapter Pattern: Using a common `Marketplace` interface.
- SQLModel: For database models.
- Litestar: Web framework for API.
- Design Patterns: Builder, State, Composite used in models/services.

Sub-packages:
- `models`: Data structures (SQLModels, DTOs, Enums).
- `repositories`: Data persistence logic (Advanced Alchemy repos, UoW).
- `services`: Business logic orchestration.
- `adapters`: External system interfaces (Marketplace).
- `controllers`: Litestar API controllers.
- `db.py`: DB engine/session setup.
- `main.py`: Litestar app entrypoint, DI config.