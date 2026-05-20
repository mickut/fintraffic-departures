from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import FintrafficApiClient, FintrafficApiError
from .const import (
    CONF_CUTOFF_MINUTES,
    CONF_NUMBER_OF_DEPARTURES,
    CONF_STOP_IDS,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)
from .models import AlertInfo, DepartureInfo, StopData

LOGGER = logging.getLogger(__name__)
HELSINKI_TIMEZONE = ZoneInfo("Europe/Helsinki")


def _parse_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, UTC)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _service_day_midnight(service_day: int) -> datetime:
    return datetime.fromtimestamp(service_day, UTC).astimezone(HELSINKI_TIMEZONE)


class FintrafficDeparturesCoordinator(DataUpdateCoordinator[dict[str, StopData]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            logger=LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_UPDATE_INTERVAL,
        )
        self.entry = entry
        self.api = FintrafficApiClient(async_get_clientsession(hass))

    async def _async_update_data(self) -> dict[str, StopData]:
        stop_ids: list[str] = list(self.entry.data[CONF_STOP_IDS])
        number_of_departures: int = self.entry.data[CONF_NUMBER_OF_DEPARTURES]
        cutoff_minutes: int = self.entry.data[CONF_CUTOFF_MINUTES]

        try:
            stops = await self.api.async_get_departures(stop_ids, number_of_departures)
        except FintrafficApiError as err:
            raise UpdateFailed(str(err)) from err

        return self._normalize_stops(stops, number_of_departures, cutoff_minutes)

    def _normalize_stops(
        self,
        stops: list[dict[str, Any]],
        number_of_departures: int,
        cutoff_minutes: int,
    ) -> dict[str, StopData]:
        minimum_departure = datetime.now(HELSINKI_TIMEZONE) + timedelta(minutes=cutoff_minutes)
        normalized: dict[str, StopData] = {}

        for stop in stops:
            stop_id = stop.get("gtfsId")
            if not stop_id:
                continue

            stop_name = stop.get("name") or stop_id
            alerts = self._normalize_alerts(stop.get("alerts") or ())
            departures = self._normalize_departures(
                stop_id=stop_id,
                stop_name=stop_name,
                stoptimes_for_patterns=stop.get("stoptimesForPatterns") or (),
                minimum_departure=minimum_departure,
                number_of_departures=number_of_departures,
            )

            normalized[stop_id] = StopData(
                stop_id=stop_id,
                stop_name=stop_name,
                departures=departures,
                alerts=alerts,
            )

        for configured_stop_id in self.entry.data[CONF_STOP_IDS]:
            normalized.setdefault(
                configured_stop_id,
                StopData(
                    stop_id=configured_stop_id,
                    stop_name=configured_stop_id,
                    departures=(),
                    alerts=(),
                ),
            )

        return normalized

    def _normalize_alerts(self, alerts: tuple[dict[str, Any], ...] | list[dict[str, Any]]) -> tuple[AlertInfo, ...]:
        now = datetime.now(UTC)
        normalized_alerts: list[AlertInfo] = []
        for alert in alerts:
            effective_start = _parse_datetime(alert.get("effectiveStartDate"))
            effective_end = _parse_datetime(alert.get("effectiveEndDate"))

            if effective_start and effective_start > now:
                continue
            if effective_end and effective_end < now:
                continue

            translations = {
                item.get("language"): item.get("text")
                for item in alert.get("alertHeaderTextTranslations") or []
                if item.get("language") and item.get("text")
            }

            normalized_alerts.append(
                AlertInfo(
                    severity=alert.get("alertSeverityLevel"),
                    header=alert.get("alertHeaderText"),
                    translations=translations,
                    effective_start=effective_start,
                    effective_end=effective_end,
                )
            )

        return tuple(normalized_alerts)

    def _normalize_departures(
        self,
        stop_id: str,
        stop_name: str,
        stoptimes_for_patterns: tuple[dict[str, Any], ...] | list[dict[str, Any]],
        minimum_departure: datetime,
        number_of_departures: int,
    ) -> tuple[DepartureInfo, ...]:
        merged_departures: list[DepartureInfo] = []

        for grouped_stoptime in stoptimes_for_patterns:
            pattern = grouped_stoptime.get("pattern") or {}
            route = pattern.get("route") or {}
            for stoptime in grouped_stoptime.get("stoptimes") or []:
                service_day = stoptime.get("serviceDay")
                scheduled_offset = stoptime.get("scheduledDeparture")
                realtime_offset = stoptime.get("realtimeDeparture")

                if not isinstance(service_day, int) or not isinstance(scheduled_offset, int):
                    continue

                service_day_midnight = _service_day_midnight(service_day)
                scheduled_datetime = service_day_midnight + timedelta(seconds=scheduled_offset)
                effective_offset = realtime_offset if isinstance(realtime_offset, int) else scheduled_offset
                departure_datetime = service_day_midnight + timedelta(seconds=effective_offset)
                realtime_state = stoptime.get("realtimeState")

                if realtime_state in {"CANCELED", "CANCELLED"}:
                    continue
                if departure_datetime <= minimum_departure:
                    continue

                delay_minutes = int((effective_offset - scheduled_offset) / 60)

                merged_departures.append(
                    DepartureInfo(
                        stop_id=stop_id,
                        stop_name=stop_name,
                        pattern_code=pattern.get("code") or "",
                        headsign=pattern.get("headsign"),
                        route_short_name=route.get("shortName"),
                        route_long_name=route.get("longName"),
                        scheduled_datetime=scheduled_datetime,
                        departure_datetime=departure_datetime,
                        realtime_state=realtime_state,
                        delay_minutes=delay_minutes,
                    )
                )

        merged_departures.sort(key=lambda departure: departure.departure_datetime)
        return tuple(merged_departures[:number_of_departures])