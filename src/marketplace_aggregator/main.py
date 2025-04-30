# src/marketplace_aggregator/main.py

import uvicorn
from litestar import Litestar, get  # Add get later for health check
from litestar.di import Provide
from typing import Dict
from sqlalchemy.ext.asyncio import AsyncSession

# --- Import Advanced Alchemy Litestar extension ---
from advanced_alchemy.extensions.litestar.plugins import (
    SQLAlchemyPlugin,
    SQLAlchemyAsyncConfig,
)

# --- Import our DB engine ---
from marketplace_aggregator.db import engine as db_engine  # Renamed to avoid clash

# --- Import Repositories ---
from marketplace_aggregator.repositories.listing_repo import ListingRepository
from marketplace_aggregator.repositories.promotional_rule_repo import (
    PromotionalRuleRepository,
)
from marketplace_aggregator.repositories.inventory_product_repo import (
    InventoryProductRepository,
)
from marketplace_aggregator.repositories.variable_product_repo import (
    VariableProductRepository,
)
from marketplace_aggregator.repositories.assembly_repo import AssemblyRepository
from marketplace_aggregator.repositories.service_product_repo import (
    ServiceProductRepository,
)

# --- Import Adapters & Service ---
from marketplace_aggregator.adapters.marketplace import Marketplace  # Interface
from marketplace_aggregator.adapters.fakeamazon_adapter import (
    FakemazonAdapter,
)  # Concrete Adapter
from marketplace_aggregator.services.listing_service import ListingService

from marketplace_aggregator.controllers.listing_controller import ListingController


# --- Configure the SQLAlchemy Plugin ---
# This handles session creation, commits/rollbacks per request,
# and makes AsyncSession available for dependency injection.
sqlalchemy_config = SQLAlchemyAsyncConfig(
    engine_instance=db_engine,  # Pass our async engine
    session_dependency_key="db_session",  # Explicitly set the session dependency key
)
sqlalchemy_plugin = SQLAlchemyPlugin(config=sqlalchemy_config)

# --- Define Dependencies for Injection ---


# Create marketplace adapters map (can be enhanced later with config loading)
async def create_marketplace_adapters() -> Dict[str, Marketplace]:
    print("Creating marketplace adapters map...")
    fakemazon_config = {"seller_id": "DI_SELLER_1", "api_key": "DI_FAKE_KEY"}
    fakemazon = FakemazonAdapter(fakemazon_config)
    return {fakemazon.name: fakemazon}


async def get_listing_repo(db_session: AsyncSession) -> ListingRepository:
    return ListingRepository(session=db_session)


async def get_promotional_rule_repo(
    db_session: AsyncSession,
) -> PromotionalRuleRepository:
    return PromotionalRuleRepository(session=db_session)


async def get_inventory_product_repo(
    db_session: AsyncSession,
) -> InventoryProductRepository:
    return InventoryProductRepository(session=db_session)


async def get_variable_product_repo(
    db_session: AsyncSession,
) -> VariableProductRepository:
    return VariableProductRepository(session=db_session)


async def get_assembly_repo(db_session: AsyncSession) -> AssemblyRepository:
    return AssemblyRepository(session=db_session)


async def get_service_product_repo(
    db_session: AsyncSession,
) -> ServiceProductRepository:
    return ServiceProductRepository(session=db_session)


async def get_listing_service(
    listing_repo: ListingRepository,
    promotional_rule_repo: PromotionalRuleRepository,
    inventory_product_repo: InventoryProductRepository,
    variable_product_repo: VariableProductRepository,
    assembly_repo: AssemblyRepository,
    service_product_repo: ServiceProductRepository,
    marketplace_adapters: Dict[str, Marketplace],
    db_session: AsyncSession,
) -> ListingService:
    return ListingService(
        listing_repo=listing_repo,
        promotional_rule_repo=promotional_rule_repo,
        inventory_product_repo=inventory_product_repo,
        variable_product_repo=variable_product_repo,
        assembly_repo=assembly_repo,
        service_product_repo=service_product_repo,
        marketplace_adapters=marketplace_adapters,
        db_session=db_session,
    )


# Define how to provide dependencies to handlers/services
dependencies = {
    # AA Repositories often implicitly get AsyncSession from the plugin
    "listing_repo": Provide(get_listing_repo, use_cache=True),
    "promotional_rule_repo": Provide(get_promotional_rule_repo, use_cache=True),
    "inventory_product_repo": Provide(get_inventory_product_repo, use_cache=True),
    "variable_product_repo": Provide(get_variable_product_repo, use_cache=True),
    "assembly_repo": Provide(get_assembly_repo, use_cache=True),
    "service_product_repo": Provide(get_service_product_repo, use_cache=True),
    # Provide the adapters map
    "marketplace_adapters": Provide(create_marketplace_adapters, use_cache=True),
    # Provide the ListingService, automatically injecting its dependencies
    "listing_service": Provide(get_listing_service, use_cache=True),
}


# Basic health check route (good practice)
@get("/")
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}


# Placeholder for the app object
# We will configure plugins, dependencies, and routes below
app = Litestar(
    route_handlers=[health_check, ListingController],
    dependencies=dependencies,
    plugins=[sqlalchemy_plugin],
)


# Add this block to run with `python -m src.marketplace_aggregator.main`
# Note: For development, running `uvicorn src.marketplace_aggregator.main:app --reload`
#       in the terminal is usually preferred for auto-reloading.
if __name__ == "__main__":
    # host="0.0.0.0" makes it accessible on the network, default is "127.0.0.1"
    # port=8000 is standard for dev APIs
    uvicorn.run(app, host="0.0.0.0", port=8000)
