path: src/marketplace_aggregator/controllers/

# Context for the Controllers Package

Implements the API layer using Litestar.

- Contains Litestar `Controller` classes.
- Uses decorators (`@get`, `@post`) for routing.
- Uses DI (`Provide`) to get service instances.
- Uses Pydantic/SQLModels for request validation and response serialization.
- Controllers are thin, delegating logic to services.
    