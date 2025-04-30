path: src/marketplace_aggregator/adapters/

# Context for the Adapters Package

Handles interaction with external systems (marketplaces).

- Defines abstract `Marketplace` interface.
- Concrete adapters (e.g., `FakemazonAdapter`) implement the interface.
- Responsible for translating between internal models/DTOs and external API formats.
- Handles API communication details (async).
- Configuration injected via `__init__`.
    