# src/marketplace_aggregator/controllers/listing_controller.py

from typing import Optional, List
from pydantic import BaseModel  # Use pydantic for request body validation

from litestar import Controller, post, get, Response
from litestar.exceptions import NotFoundException

# Import the service
from marketplace_aggregator.models.listing import Listing
from marketplace_aggregator.repositories.listing_repo import ListingRepository
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

    @post("/", summary="Create Listing From Rule")  # Corresponds to POST /listings
    async def create_listing_from_rule(
        self,
        data: ListByRuleRequest,  # Request body, auto-validated by Litestar/Pydantic
        listing_service: ListingService,  # Dependency Injected by Litestar
    ) -> Response[ListingResponse]:  # Return type (will be auto-serialized to JSON)
        """
        API endpoint to trigger listing creation based on a PromotionalRule ID.
        """
        listing_id = await listing_service.list_item_on_marketplace(
            rule_id=data.rule_id
        )

        if listing_id:
            response_data = ListingResponse(status="success", listing_id=listing_id)
            print(f"Controller: Response: {response_data}")
            return Response(
                content=response_data,
                status_code=201
            )
        else:
            # Ideally return more specific error codes (404, 400, 500) later
            response_data = ListingResponse(status="error", error="Failed to create listing.")
            print(f"Controller: Response: {response_data}")
            return Response(
                content=response_data,
                status_code=400
            )

    @get("/{marketplace_name:str}/{listing_id:str}", summary="Get Specific Listing")
    async def get_listing(
        self,
        marketplace_name: str,  # Automatically extracted from path
        listing_id: str,  # Automatically extracted from path
        listing_repo: ListingRepository,
    ) -> Listing:  # Return the Listing model directly
        """
        API endpoint to retrieve details of a specific listing
        by its marketplace name and marketplace-assigned listing ID.
        """
        listing = await listing_repo.get_by_composite_id(marketplace_name, listing_id)
        if not listing:
            print(f"Controller: Listing not found for {marketplace_name}/{listing_id}")
            raise NotFoundException(
                f"Listing {listing_id} not found on {marketplace_name}"
            )

        print(f"Controller: Returning listing {listing_id}")
        return listing  # Litestar handles serialization to JSON

    # --- TODO: Add GET endpoint for listing all listings (maybe with pagination) ---
    @get("/", summary="List All Listings")
    async def list_listings(
        self,
        listing_repo: ListingRepository,
    ) -> List[Listing]:
        listings = await listing_repo.list_all()
        print(f"Controller: Returning {len(listings)} listings")
        return listings
