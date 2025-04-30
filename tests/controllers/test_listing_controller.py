# tests/controllers/test_listing_controller.py

from marketplace_aggregator.models.listing import Listing
from marketplace_aggregator.repositories.listing_repo import ListingRepository
import pytest
from unittest.mock import AsyncMock, MagicMock  # Need AsyncMock for mocking async method

from litestar import Litestar
from litestar.testing import AsyncTestClient

# Import the service we are mocking and the request/response models
from marketplace_aggregator.services.listing_service import ListingService

# Import the Pydantic models used by the endpoint
from marketplace_aggregator.controllers.listing_controller import (
    ListByRuleRequest,
    ListingResponse,
)

from datetime import datetime, timezone


@pytest.mark.asyncio
async def test_create_listing_success(
    test_client: AsyncTestClient[Litestar],  # Inject the test client fixture
    mocker,  # Inject pytest-mock's mocker fixture
):
    """
    Test POST /listings endpoint for successful listing creation.
    """
    # Arrange
    rule_id_to_test = 5
    expected_marketplace_listing_id = "FKZ-RULE5-TEST123"
    request_data = ListByRuleRequest(
        rule_id=rule_id_to_test
    ).model_dump()  # Use Pydantic model

    # --- Mock the ListingService method ---
    # We patch the method within the actual service module where the controller imports it from
    mock_service_call = mocker.patch.object(
        ListingService,  # The class containing the method
        "list_item_on_marketplace",  # The name of the async method to patch
        new_callable=AsyncMock,  # Use AsyncMock for awaitable behavior
        return_value=expected_marketplace_listing_id,  # Configure return value
    )
    # -------------------------------------

    # Act: Make the API request using the test client
    response = await test_client.post(
        "/listings", json=request_data
    )  # Use trailing slash if needed by routes

    # Assert
    # 1. Check HTTP status code (e.g., 201 Created or 200 OK)
    #    Using 200 OK for simplicity now, can change later.
    assert response.status_code in [200, 201]  # Or 201 if you prefer for creation

    # 2. Check the response body
    response_data = response.json()
    expected_response = ListingResponse(
        status="success", listing_id=expected_marketplace_listing_id
    ).model_dump()
    assert response_data == expected_response

    # 3. Verify the mocked service method was called correctly
    mock_service_call.assert_awaited_once_with(rule_id=rule_id_to_test)


@pytest.mark.asyncio
async def test_create_listing_service_fails(
    test_client: AsyncTestClient[Litestar], mocker
):
    """
    Test POST /listings endpoint when the listing service fails (returns None).
    """
    # Arrange
    rule_id_to_test = 999  # Use a different ID for clarity
    request_data = ListByRuleRequest(rule_id=rule_id_to_test).model_dump()

    # Mock the ListingService method to return None, simulating failure
    mock_service_call = mocker.patch.object(
        ListingService,
        "list_item_on_marketplace",
        new_callable=AsyncMock,
        return_value=None,  # Simulate failure
    )

    # Act
    response = await test_client.post("/listings", json=request_data)

    # Assert
    # 1. Check status code - have to be 400
    assert response.status_code == 400

    # 2. Check the response body indicates an error
    response_data = response.json()
    expected_response = ListingResponse(
        status="error", error="Failed to create listing."
    ).model_dump()
    assert response_data == expected_response

    # 3. Verify the mocked service method was called
    mock_service_call.assert_awaited_once_with(rule_id=rule_id_to_test)


@pytest.mark.asyncio
async def test_create_listing_invalid_input_type(
    test_client: AsyncTestClient[Litestar],
    mocker,  # Include mocker even if not used directly, good practice
):
    """
    Test POST /listings with invalid data type for rule_id.
    Expects a 422 Unprocessable Entity response from Litestar/Pydantic.
    """
    # Arrange: Prepare invalid request data
    invalid_data = {"rule_id": "this-is-not-an-integer"}

    # Mock the service method just to ensure it's NOT called
    mock_service_call = mocker.patch.object(
        ListingService, "list_item_on_marketplace", new_callable=AsyncMock
    )

    # Act: Make the API request with invalid data
    response = await test_client.post("/listings", json=invalid_data)

    # Assert
    # 1. Check for 422 status code
    assert response.status_code == 400

    # 2. Optional: Check response body for validation error details
    #    Litestar/Pydantic provide detailed error messages.
    response_data = response.json()
    assert "detail" in response_data
    # print(response_data) # Uncomment to see the detailed error structure

    # 3. Verify the service method was *NOT* called
    mock_service_call.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_listing_missing_input_field(
    test_client: AsyncTestClient[Litestar], mocker
):
    """
    Test POST /listings with missing rule_id field.
    Expects a 422 Unprocessable Entity response.
    """
    # Arrange: Prepare invalid request data (missing required field)
    invalid_data = {"other_field": 123}  # rule_id is missing

    mock_service_call = mocker.patch.object(
        ListingService, "list_item_on_marketplace", new_callable=AsyncMock
    )

    # Act
    response = await test_client.post("/listings", json=invalid_data)

    # Assert
    assert response.status_code == 400
    mock_service_call.assert_not_awaited()

@pytest.mark.asyncio
async def test_list_listings_success(
    test_client: AsyncTestClient[Litestar], # Use Litestar's test client
    mocker # Use mocker to patch the repository dependency provider if needed, or inject mock repo
):
    """Test GET /listings endpoint for successfully retrieving all listings."""
    # Arrange
    # Create some mock Listing data that the repository should return
    mock_listing1 = Listing(
        id=1, product_identifier="SKU001", marketplace_name="TestPlace",
        marketplace_listing_id="LST1", status="active", rule_id=1,
        created_at=datetime.now(timezone.utc),
        last_updated_at=datetime.now(timezone.utc)
    )
    mock_listing2 = Listing(
        id=2, product_identifier="SKU002", marketplace_name="TestPlace",
        marketplace_listing_id="LST2", status="pending", rule_id=2,
        created_at=datetime.now(timezone.utc),
        last_updated_at=datetime.now(timezone.utc)
    )
    mock_listings_list = [mock_listing1, mock_listing2]

    # --- Mock the ListingRepository ---
    mock_list_all = mocker.patch.object(
        ListingRepository, # Patch the actual repository class
        "list_all",        # The method to patch
        new_callable=AsyncMock,
        return_value=mock_listings_list # Configure return value
    )
    # --- End Mocking ---

    # Act: Make the API request
    response = await test_client.get("/listings")

    # Assert
    # 1. Check status code
    assert response.status_code == 200

    # 2. Check response body structure and content
    response_data = response.json()
    assert isinstance(response_data, list)
    print(f"Controller: Response data: {response_data}")
    assert len(response_data) == len(mock_listings_list)

    # Convert models to dicts for comparison (assuming serialization works)
    # Note: SQLModel/Pydantic might serialize datetime differently than default json.dumps
    # Be mindful of timestamp formats if comparing dicts directly.
    # Comparing essential fields is often more robust.
    expected_data = [listing.model_dump(exclude={'_state'}) for listing in mock_listings_list] # Use model_dump
    # Adjust expected data if serialization format differs (e.g., datetime strings)
    assert response_data[0]['marketplace_listing_id'] == expected_data[0]['marketplace_listing_id']
    assert response_data[1]['marketplace_listing_id'] == expected_data[1]['marketplace_listing_id']
    assert response_data[0]['product_identifier'] == expected_data[0]['product_identifier']
    assert response_data[1]['product_identifier'] == expected_data[1]['product_identifier']

    # 3. Verify the repository method was called
    mock_list_all.assert_awaited_once()