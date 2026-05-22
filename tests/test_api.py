from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest
from aiohttp import ClientError

from custom_components.transit_departures.api import TransitApiClient, TransitApiError
from tests.fixtures.api_payloads import graphql_response


@pytest.mark.asyncio
async def test_async_search_stops_parses_and_deduplicates() -> None:
    response = Mock()
    response.raise_for_status.return_value = None
    response.json = AsyncMock(return_value={
        "features": [
            {
                "properties": {
                    "id": "GTFS:HSL:1040273#H1243",
                    "label": "Helsinki Main",
                }
            },
            {
                "properties": {
                    "gtfsId": "HSL:1040273",
                    "name": "Helsinki Main Duplicate",
                }
            },
            {"properties": {"id": "HSL:1041402", "name": "Kamppi"}},
        ]
    })

    session = AsyncMock()
    session.get.return_value = response

    client = TransitApiClient(session)
    results = await client.async_search_stops("helsinki")

    assert [result.stop_id for result in results] == ["HSL:1040273", "HSL:1041402"]
    assert results[0].label == "Helsinki Main"


@pytest.mark.asyncio
async def test_async_search_stops_raises_on_http_error() -> None:
    session = AsyncMock()
    session.get.side_effect = ClientError("boom")

    client = TransitApiClient(session)

    with pytest.raises(TransitApiError, match="Search request failed"):
        await client.async_search_stops("helsinki")


@pytest.mark.asyncio
async def test_async_get_departures_returns_stops() -> None:
    response = Mock()
    response.raise_for_status.return_value = None
    response.json = AsyncMock(return_value=graphql_response())

    session = AsyncMock()
    session.post.return_value = response

    client = TransitApiClient(session)
    stops = await client.async_get_departures(["HSL:1040273"], 4)

    assert len(stops) == 1
    assert stops[0]["gtfsId"] == "HSL:1040273"


@pytest.mark.asyncio
async def test_async_get_departures_raises_on_graphql_errors() -> None:
    response = Mock()
    response.raise_for_status.return_value = None
    response.json = AsyncMock(return_value={"errors": [{"message": "failure"}]})

    session = AsyncMock()
    session.post.return_value = response

    client = TransitApiClient(session)

    with pytest.raises(TransitApiError, match="GraphQL errors returned"):
        await client.async_get_departures(["HSL:1040273"], 4)
