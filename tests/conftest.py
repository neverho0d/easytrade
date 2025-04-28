# tests/conftest.py

import pytest
from typing import AsyncIterator

from litestar import Litestar
from litestar.testing import AsyncTestClient

# Import your Litestar application instance
from marketplace_aggregator.main import app


app.debug = True


@pytest.fixture
async def test_client() -> AsyncIterator[AsyncTestClient[Litestar]]:
    """Fixture to create an httpx test client for the Litestar app."""
    # LitestarTestClient is based on httpx.AsyncClient
    # We pass the 'app' instance to it.
    async with AsyncTestClient(app=app) as client:
        print("Test client created")
        yield client
    print("Test client closed")


# Note: For more complex setups involving overriding dependencies during testing,
# Litestar's testing docs show more advanced fixture patterns, but this works
# when we primarily use mocker.patch.object within the tests themselves.
