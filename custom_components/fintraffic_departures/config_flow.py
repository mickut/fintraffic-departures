from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import FintrafficApiClient, FintrafficApiError, StopSearchResult

from .const import (
    CONF_CUTOFF_MINUTES,
    CONF_NUMBER_OF_DEPARTURES,
    CONF_SELECTED_STOP_IDS,
    CONF_STOP_IDS,
    CONF_STOP_LOOKUP_QUERY,
    CONF_UPDATE_INTERVAL_MINUTES,
    DEFAULT_CUTOFF_MINUTES,
    DEFAULT_NUMBER_OF_DEPARTURES,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    DOMAIN,
    normalize_stop_id,
)


def _parse_stop_ids(value: str) -> list[str]:
    return list(dict.fromkeys(normalize_stop_id(item) for item in value.split(",") if item.strip()))


class FintrafficDeparturesConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._search_results: list[StopSearchResult] = []
        self._pending_config: dict[str, Any] = {}

    async def async_step_user(self, user_input: Mapping[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            stop_ids = _parse_stop_ids(user_input[CONF_STOP_IDS])
            lookup_query = user_input.get(CONF_STOP_LOOKUP_QUERY, "").strip()
            number_of_departures = user_input[CONF_NUMBER_OF_DEPARTURES]
            cutoff_minutes = user_input[CONF_CUTOFF_MINUTES]
            update_interval_minutes = user_input[CONF_UPDATE_INTERVAL_MINUTES]

            if not stop_ids:
                if lookup_query:
                    self._pending_config = {
                        CONF_NUMBER_OF_DEPARTURES: number_of_departures,
                        CONF_CUTOFF_MINUTES: cutoff_minutes,
                        CONF_UPDATE_INTERVAL_MINUTES: update_interval_minutes,
                    }
                    try:
                        api = FintrafficApiClient(async_get_clientsession(self.hass))
                        self._search_results = await api.async_search_stops(lookup_query)
                    except FintrafficApiError:
                        errors[CONF_STOP_LOOKUP_QUERY] = "lookup_failed"
                    else:
                        if self._search_results:
                            return await self.async_step_select_stops()
                        errors[CONF_STOP_LOOKUP_QUERY] = "no_search_results"
                else:
                    errors[CONF_STOP_IDS] = "invalid_stop_ids"
            elif number_of_departures < 1:
                errors[CONF_NUMBER_OF_DEPARTURES] = "invalid_departure_count"
            elif cutoff_minutes < 0:
                errors[CONF_CUTOFF_MINUTES] = "invalid_cutoff_minutes"
            elif update_interval_minutes < 1:
                errors[CONF_UPDATE_INTERVAL_MINUTES] = "invalid_update_interval_minutes"
            else:
                await self.async_set_unique_id(
                    "|".join(stop_ids)
                    + f":{number_of_departures}:{cutoff_minutes}:{update_interval_minutes}"
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Fintraffic Departures ({', '.join(stop_ids)})",
                    data={
                        CONF_STOP_IDS: stop_ids,
                        CONF_NUMBER_OF_DEPARTURES: number_of_departures,
                        CONF_CUTOFF_MINUTES: cutoff_minutes,
                        CONF_UPDATE_INTERVAL_MINUTES: update_interval_minutes,
                    },
                )

        schema = vol.Schema(
            {
                vol.Optional(CONF_STOP_LOOKUP_QUERY, default=""): str,
                vol.Optional(CONF_STOP_IDS, default=""): str,
                vol.Required(
                    CONF_NUMBER_OF_DEPARTURES,
                    default=DEFAULT_NUMBER_OF_DEPARTURES,
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=20)),
                vol.Required(
                    CONF_CUTOFF_MINUTES,
                    default=DEFAULT_CUTOFF_MINUTES,
                ): vol.All(vol.Coerce(int), vol.Range(min=0, max=180)),
                vol.Required(
                    CONF_UPDATE_INTERVAL_MINUTES,
                    default=DEFAULT_UPDATE_INTERVAL_MINUTES,
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=1440)),
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_select_stops(self, user_input: Mapping[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            selected_stop_ids = user_input[CONF_SELECTED_STOP_IDS]
            if not selected_stop_ids:
                errors[CONF_SELECTED_STOP_IDS] = "invalid_stop_ids"
            else:
                stop_ids = list(selected_stop_ids)
                await self.async_set_unique_id(
                    "|".join(stop_ids)
                    + f":{self._pending_config[CONF_NUMBER_OF_DEPARTURES]}:{self._pending_config[CONF_CUTOFF_MINUTES]}:{self._pending_config[CONF_UPDATE_INTERVAL_MINUTES]}"
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Fintraffic Departures ({', '.join(stop_ids)})",
                    data={
                        CONF_STOP_IDS: stop_ids,
                        CONF_NUMBER_OF_DEPARTURES: self._pending_config[CONF_NUMBER_OF_DEPARTURES],
                        CONF_CUTOFF_MINUTES: self._pending_config[CONF_CUTOFF_MINUTES],
                        CONF_UPDATE_INTERVAL_MINUTES: self._pending_config[CONF_UPDATE_INTERVAL_MINUTES],
                    },
                )

        options = [
            selector.SelectOptionDict(value=result.stop_id, label=f"{result.label} ({result.stop_id})")
            for result in self._search_results
        ]
        schema = vol.Schema(
            {
                vol.Required(CONF_SELECTED_STOP_IDS): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=options,
                        multiple=True,
                    )
                )
            }
        )

        return self.async_show_form(step_id="select_stops", data_schema=schema, errors=errors)