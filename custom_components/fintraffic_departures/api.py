from __future__ import annotations

from typing import Any

from aiohttp import ClientError, ClientSession

from .const import DIGITRAFFIC_USER, GRAPHQL_ENDPOINT_VALUE, GRAPHQL_URL, GRAPHQL_USER_HEADER, QUERY_GET_DEPARTURES


class FintrafficApiError(Exception):
    """Raised when the Fintraffic API request fails."""


class FintrafficApiClient:
    def __init__(self, session: ClientSession) -> None:
        self._session = session

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
            raise FintrafficApiError(f"Request failed: {err}") from err
        except ValueError as err:
            raise FintrafficApiError("Response was not valid JSON") from err

        errors = response_json.get("errors")
        if errors:
            raise FintrafficApiError(f"GraphQL errors returned: {errors}")

        data = response_json.get("data")
        if not isinstance(data, dict):
            raise FintrafficApiError("Response did not contain a data object")

        stops = data.get("stops")
        if not isinstance(stops, list):
            raise FintrafficApiError("Response did not contain a stops array")

        return stops