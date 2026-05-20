from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_CUTOFF_MINUTES,
    CONF_NUMBER_OF_DEPARTURES,
    CONF_STOP_IDS,
    CONF_UPDATE_INTERVAL_MINUTES,
    DEFAULT_CUTOFF_MINUTES,
    DEFAULT_NUMBER_OF_DEPARTURES,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    DOMAIN,
)


def _parse_stop_ids(value: str) -> list[str]:
    return list(dict.fromkeys(item.strip() for item in value.split(",") if item.strip()))


class FintrafficDeparturesConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: Mapping[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            stop_ids = _parse_stop_ids(user_input[CONF_STOP_IDS])
            number_of_departures = user_input[CONF_NUMBER_OF_DEPARTURES]
            cutoff_minutes = user_input[CONF_CUTOFF_MINUTES]
            update_interval_minutes = user_input[CONF_UPDATE_INTERVAL_MINUTES]

            if not stop_ids:
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
                vol.Required(CONF_STOP_IDS): str,
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