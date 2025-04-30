path: .

# Project Overview: Marketplace Aggregator SaaS

This project is a SaaS application designed to help sellers list and manage products across multiple e-commerce marketplaces (like Amazon, eBay, Etsy).

Core Goal: Provide a unified interface to manage product data, listing rules, and potentially orders/inventory sync across different marketplace APIs.

Tech Stack:
- Language: Python (^3.11)
- Web Framework: Litestar (ASGI)
- Database: PostgreSQL (via Docker)
- ORM/Data Layer: SQLModel
- Data Access Pattern: Repository Pattern (using Advanced Alchemy)
- Async: Heavily uses asyncio/async/await
- Dependencies: Managed by Poetry
- Testing: pytest, pytest-asyncio, pytest-cov, unittest.mock
- Linting/Formatting: Ruff
- Type Checking: MyPy
- CI: GitHub Actions

See other rule files scoped to specific directories for more detailed context.