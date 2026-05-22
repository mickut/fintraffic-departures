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
    CONF_DISABLE_STOP_SUFFIX,
    CONF_NUMBER_OF_DEPARTURES,
    CONF_PREFIX,
    CONF_STOP_SUFFIX,
    CONF_STOP_ID,
    CONF_STOP_LOOKUP_QUERY,
    CONF_SUFFIX,
    CONF_UPDATE_INTERVAL_MINUTES,
    DEFAULT_CUTOFF_MINUTES,
    DEFAULT_DISABLE_STOP_SUFFIX,
    DEFAULT_NUMBER_OF_DEPARTURES,
    DEFAULT_PREFIX,
    DEFAULT_SUFFIX,
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

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> config_entries.OptionsFlow:
        return TransitDeparturesOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: Mapping[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            number_of_departures = user_input[CONF_NUMBER_OF_DEPARTURES]
            cutoff_minutes = user_input[CONF_CUTOFF_MINUTES]
            update_interval_minutes = user_input[CONF_UPDATE_INTERVAL_MINUTES]
            prefix = user_input.get(CONF_PREFIX, "")
            suffix = user_input.get(CONF_SUFFIX, "")

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
                        CONF_PREFIX: prefix,
                        CONF_SUFFIX: suffix,
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
                vol.Required(
                    CONF_PREFIX,
                    default=DEFAULT_PREFIX,
                ): selector.TextSelector(),
                vol.Required(
                    CONF_SUFFIX,
                    default=DEFAULT_SUFFIX,
                ): selector.TextSelector(),
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
                stop_suffix = user_input.get(CONF_STOP_SUFFIX, "").strip()
                disable_stop_suffix = bool(user_input.get(CONF_DISABLE_STOP_SUFFIX, False))
                self._search_results = []
                return await self._async_create_stop_subentry(
                    stop_id,
                    title,
                    stop_suffix=stop_suffix,
                    disable_stop_suffix=disable_stop_suffix,
                )

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
                ),
                vol.Optional(CONF_STOP_SUFFIX, default=""): selector.TextSelector(),
                vol.Required(
                    CONF_DISABLE_STOP_SUFFIX,
                    default=DEFAULT_DISABLE_STOP_SUFFIX,
                ): selector.BooleanSelector(),
            }
        )

        return self.async_show_form(step_id="select_stop", data_schema=schema, errors=errors)

    async def _async_create_stop_subentry(
        self,
        stop_id: str,
        title: str,
        stop_suffix: str = "",
        disable_stop_suffix: bool = DEFAULT_DISABLE_STOP_SUFFIX,
    ) -> SubentryFlowResult:
        for existing_subentry in self._get_entry().subentries.values():
            if existing_subentry.unique_id == stop_id:
                return self.async_abort(reason="already_configured")

        subentry_data: dict[str, Any] = {CONF_STOP_ID: stop_id}
        subentry_data[CONF_DISABLE_STOP_SUFFIX] = bool(disable_stop_suffix)
        if not disable_stop_suffix and stop_suffix:
            subentry_data[CONF_STOP_SUFFIX] = stop_suffix

        return self.async_create_entry(
            title=title,
            unique_id=stop_id,
            data=subentry_data,
        )


class TransitDeparturesOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: Mapping[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=dict(user_input))

        prefix_default = self._config_entry.options.get(
            CONF_PREFIX,
            self._config_entry.data.get(CONF_PREFIX, DEFAULT_PREFIX),
        )
        suffix_default = self._config_entry.options.get(
            CONF_SUFFIX,
            self._config_entry.data.get(CONF_SUFFIX, DEFAULT_SUFFIX),
        )

        schema = vol.Schema(
            {
                vol.Required(CONF_PREFIX, default=prefix_default): selector.TextSelector(),
                vol.Required(CONF_SUFFIX, default=suffix_default): selector.TextSelector(),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema, errors={})