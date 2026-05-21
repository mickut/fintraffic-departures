from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aiohttp import ClientError, ClientSession

from .const import (
    DIGITRAFFIC_USER,
    GEOCODING_SEARCH_LAYERS,
    GEOCODING_SEARCH_SIZE,
    GEOCODING_SEARCH_SOURCES,
    GEOCODING_SEARCH_URL,
    GRAPHQL_ENDPOINT_VALUE,
    GRAPHQL_URL,
    GRAPHQL_USER_HEADER,
    QUERY_GET_DEPARTURES,
    normalize_stop_id,
)


class TransitApiError(Exception):
    """Raised when the transit API request fails."""


@dataclass(frozen=True, slots=True)
class StopSearchResult:
    stop_id: str
    label: str


class TransitApiClient:
    def __init__(self, session: ClientSession) -> None:
        self._session = session

    async def async_search_stops(self, query: str) -> list[StopSearchResult]:
        headers = {
            "accept": "application/json",
            GRAPHQL_USER_HEADER: DIGITRAFFIC_USER,
        }
        params = {
            "text": query,
            "size": str(GEOCODING_SEARCH_SIZE),
            "sources": GEOCODING_SEARCH_SOURCES,
            "layers": GEOCODING_SEARCH_LAYERS,
        }

        try:
            response = await self._session.get(
                GEOCODING_SEARCH_URL,
                params=params,
                headers=headers,
            )
            response.raise_for_status()
            response_json = await response.json()
        except ClientError as err:
            raise TransitApiError(f"Search request failed: {err}") from err
        except ValueError as err:
            raise TransitApiError("Search response was not valid JSON") from err

        features = response_json.get("features")
        if not isinstance(features, list):
            raise TransitApiError("Search response did not contain a features array")

        results: list[StopSearchResult] = []
        seen_stop_ids: set[str] = set()
        for feature in features:
            properties = feature.get("properties") or {}
            raw_stop_id = properties.get("id") or properties.get("gtfsId")
            if not isinstance(raw_stop_id, str):
                continue

            stop_id = normalize_stop_id(raw_stop_id)
            if not stop_id or stop_id in seen_stop_ids:
                continue

            label = properties.get("label") or properties.get("name") or stop_id
            results.append(StopSearchResult(stop_id=stop_id, label=str(label)))
            seen_stop_ids.add(stop_id)

        return results

    async def async_get_departures(
        self,
        stop_ids: list[str],
        number_of_departures: int,
    ) -> list[dict[str, Any]]:
        payload = {
            "operationName": "GetDeparturesForStops",
            "variables": {
                "ids": stop_ids,
                "numberOfDepartures": number_of_departures,
            },
            "query": QUERY_GET_DEPARTURES,
        }
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "graphql-endpoint": GRAPHQL_ENDPOINT_VALUE,
            GRAPHQL_USER_HEADER: DIGITRAFFIC_USER,
        }

        try:
            response = await self._session.post(GRAPHQL_URL, json=payload, headers=headers)
            response.raise_for_status()
            response_json = await response.json()
        except ClientError as err:
            raise TransitApiError(f"Request failed: {err}") from err
        except ValueError as err:
            raise TransitApiError("Response was not valid JSON") from err

        errors = response_json.get("errors")
        if errors:
            raise TransitApiError(f"GraphQL errors returned: {errors}")

        data = response_json.get("data")
        if not isinstance(data, dict):
            raise TransitApiError("Response did not contain a data object")

        stops = data.get("stops")
        if not isinstance(stops, list):
            raise TransitApiError("Response did not contain a stops array")

        return stops