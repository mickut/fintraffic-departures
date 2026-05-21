from __future__ import annotations

from collections.abc import Mapping
import json
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import (
    SOURCE_USER,
    ConfigEntry,
    ConfigFlowResult,
    ConfigSubentryFlow,
    FlowType,
    SubentryFlowContext,
    SubentryFlowResult,
)
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import TransitApiClient, TransitApiError

from .const import (
    CONF_CUTOFF_MINUTES,
    CONF_NUMBER_OF_DEPARTURES,
    CONF_STOP_ID,
    CONF_STOP_LOOKUP_QUERY,
    CONF_UPDATE_INTERVAL_MINUTES,
    DEFAULT_CUTOFF_MINUTES,
    DEFAULT_NUMBER_OF_DEPARTURES,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    DOMAIN,
    SUBENTRY_TYPE_STOP,
    normalize_stop_id,
)


def _normalize_single_stop_id(value: str) -> str:
    return normalize_stop_id(value) if value.strip() else ""


def _encode_stop_selection(stop_id: str, title: str) -> str:
    return json.dumps({"stop_id": stop_id, "title": title}, separators=(",", ":"))


def _decode_stop_selection(value: str) -> tuple[str, str] | None:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return None

    if not isinstance(payload, dict):
        return None

    stop_id = payload.get("stop_id")
    title = payload.get("title")
    if not isinstance(stop_id, str) or not isinstance(title, str):
        return None

    normalized_stop_id = normalize_stop_id(stop_id)
    if not normalized_stop_id:
        return None

    return normalized_stop_id, title.strip() or normalized_stop_id


class TransitDeparturesConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    MINOR_VERSION = 2

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Return supported stop subentries."""
        return {SUBENTRY_TYPE_STOP: TransitStopSubentryFlowHandler}

    async def async_step_user(
        self, user_input: Mapping[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            number_of_departures = user_input[CONF_NUMBER_OF_DEPARTURES]
            cutoff_minutes = user_input[CONF_CUTOFF_MINUTES]
            update_interval_minutes = user_input[CONF_UPDATE_INTERVAL_MINUTES]

            if number_of_departures < 1:
                errors[CONF_NUMBER_OF_DEPARTURES] = "invalid_departure_count"
            elif cutoff_minutes < 0:
                errors[CONF_CUTOFF_MINUTES] = "invalid_cutoff_minutes"
            elif update_interval_minutes < 1:
                errors[CONF_UPDATE_INTERVAL_MINUTES] = "invalid_update_interval_minutes"
            else:
                return self.async_create_entry(
                    title="Transit Departures Finland",
                    data={
                        CONF_NUMBER_OF_DEPARTURES: number_of_departures,
                        CONF_CUTOFF_MINUTES: cutoff_minutes,
                        CONF_UPDATE_INTERVAL_MINUTES: update_interval_minutes,
                    },
                )

        schema = vol.Schema(
            {
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

    async def async_on_create_entry(self, result: ConfigFlowResult) -> ConfigFlowResult:
        """Start the first stop subentry flow after creating the main entry."""
        subentry_result = await self.hass.config_entries.subentries.async_init(
            (result["result"].entry_id, SUBENTRY_TYPE_STOP),
            context=SubentryFlowContext(source=SOURCE_USER),
        )
        result["next_flow"] = (
            FlowType.CONFIG_SUBENTRIES_FLOW,
            subentry_result["flow_id"],
        )
        return result


class TransitStopSubentryFlowHandler(ConfigSubentryFlow):
    """Handle stop subentries."""

    def __init__(self) -> None:
        self._search_results: list[dict[str, str]] = []

    @staticmethod
    def _user_schema() -> vol.Schema:
        return vol.Schema(
            {
                vol.Optional(CONF_STOP_LOOKUP_QUERY, default=""): str,
                vol.Optional(CONF_STOP_ID, default=""): str,
            }
        )

    async def async_step_user(
        self, user_input: Mapping[str, Any] | None = None
    ) -> SubentryFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            stop_id = _normalize_single_stop_id(user_input.get(CONF_STOP_ID, ""))
            lookup_query = user_input.get(CONF_STOP_LOOKUP_QUERY, "").strip()

            if stop_id:
                return await self._async_create_stop_subentry(stop_id, stop_id)
            if lookup_query:
                try:
                    api = TransitApiClient(async_get_clientsession(self.hass))
                    search_results = await api.async_search_stops(lookup_query)
                except TransitApiError:
                    errors[CONF_STOP_LOOKUP_QUERY] = "lookup_failed"
                else:
                    self._search_results = [
                        {"stop_id": result.stop_id, "title": result.label}
                        for result in search_results
                    ]
                    if self._search_results:
                        return await self.async_step_select_stop()
                    errors[CONF_STOP_LOOKUP_QUERY] = "no_search_results"
            else:
                errors[CONF_STOP_ID] = "invalid_stop_id"

        schema = self._user_schema()

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_select_stop(
        self, user_input: Mapping[str, Any] | None = None
    ) -> SubentryFlowResult:
        errors: dict[str, str] = {}
        options = [
            selector.SelectOptionDict(
                value=_encode_stop_selection(result["stop_id"], result["title"]),
                label=f"{result['title']} ({result['stop_id']})",
            )
            for result in self._search_results
        ]

        if user_input is not None:
            selection = _decode_stop_selection(user_input[CONF_STOP_ID])
            if selection is None:
                errors[CONF_STOP_ID] = "invalid_stop_id"
            else:
                stop_id, title = selection
                self._search_results = []
                return await self._async_create_stop_subentry(stop_id, title)

        if not options:
            return self.async_show_form(
                step_id="user",
                data_schema=self._user_schema(),
                errors={CONF_STOP_LOOKUP_QUERY: "no_search_results"},
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_STOP_ID): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=options,
                    )
                )
            }
        )

        return self.async_show_form(step_id="select_stop", data_schema=schema, errors=errors)

    async def _async_create_stop_subentry(
        self,
        stop_id: str,
        title: str,
    ) -> SubentryFlowResult:
        for existing_subentry in self._get_entry().subentries.values():
            if existing_subentry.unique_id == stop_id:
                return self.async_abort(reason="already_configured")

        return self.async_create_entry(
            title=title,
            unique_id=stop_id,
            data={CONF_STOP_ID: stop_id},
        )