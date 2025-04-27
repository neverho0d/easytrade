# src/marketplace_aggregator/controllers/listing_controller.py

from typing import Optional
from litestar import Controller, post
from pydantic import BaseModel  # Use pydantic for request body validation

# Import the service
from marketplace_aggregator.services.listing_service import ListingService


# Define the request body structure
class ListByRuleRequest(BaseModel):
    rule_id: int


class ListingResponse(BaseModel):
    status: str
    listing_id: Optional[str] = None
    error: Optional[str] = None


class ListingController(Controller):
    path = "/listings"  # Base path for routes in this controller

    @post("/")  # Corresponds to POST /listings
    async def create_listing_from_rule(
        self,
        data: ListByRuleRequest,  # Request body, auto-validated by Litestar/Pydantic
        listing_service: ListingService,  # Dependency Injected by Litestar
    ) -> ListingResponse:  # Return type (will be auto-serialized to JSON)
        """
        API endpoint to trigger listing creation based on a PromotionalRule ID.
        """
        listing_id = await listing_service.list_item_on_marketplace(
            rule_id=data.rule_id
        )

        if listing_id:
            return ListingResponse(status="success", listing_id=listing_id)
        else:
            # Ideally return more specific error codes (404, 400, 500) later
            return ListingResponse(status="error", error="Failed to create listing.")
