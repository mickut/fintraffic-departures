from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from custom_components.transit_departures.api import TransitApiClient
from tests.fixtures.api_payloads import graphql_stops_payload, search_results


@pytest.fixture
def mock_api_client() -> AsyncMock:
    """Mock TransitApiClient with deterministic, network-free responses."""
    api = AsyncMock(spec=TransitApiClient)
    api.async_search_stops.return_value = search_results()
    api.async_get_departures.return_value = graphql_stops_payload()
    return api
