from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from custom_components.transit_departures.api import TransitApiError
from custom_components.transit_departures.const import (
    CONF_CUTOFF_MINUTES,
    CONF_NUMBER_OF_DEPARTURES,
    CONF_STOP_ID,
    CONF_UPDATE_INTERVAL_MINUTES,
    SUBENTRY_TYPE_STOP,
)
from custom_components.transit_departures.coordinator import (
    HELSINKI_TIMEZONE,
    TransitDeparturesCoordinator,
)
from homeassistant.helpers.update_coordinator import UpdateFailed


def _coordinator_instance() -> TransitDeparturesCoordinator:
    """Create coordinator instance without running Home Assistant setup logic."""
    return object.__new__(TransitDeparturesCoordinator)


def _build_entry(stop_id: str = "HSL:1040273") -> SimpleNamespace:
    return SimpleNamespace(
        data={
            CONF_NUMBER_OF_DEPARTURES: 4,
            CONF_CUTOFF_MINUTES: 0,
            CONF_UPDATE_INTERVAL_MINUTES: 15,
        },
        subentries={
            "sub-1": SimpleNamespace(
                subentry_type=SUBENTRY_TYPE_STOP,
                data={CONF_STOP_ID: stop_id},
            )
        },
    )


def test_normalize_departures_filters_canceled_and_cutoff() -> None:
    coordinator = _coordinator_instance()
    service_day = int(datetime(2026, 5, 22, tzinfo=UTC).timestamp())

    minimum_departure = datetime(2026, 5, 22, 9, 0, tzinfo=HELSINKI_TIMEZONE)
    departures = coordinator._normalize_departures(
        stop_id="HSL:1040273",
        stop_name="Helsinki Main",
        stoptimes_for_patterns=[
            {
                "pattern": {
                    "code": "550",
                    "headsign": "Itakeskus",
                    "route": {"shortName": "550", "longName": "Jokeri"},
                },
                "stoptimes": [
                    {
                        "serviceDay": service_day,
                            "scheduledDeparture": 5 * 3600 + 30 * 60,
                            "realtimeDeparture": 5 * 3600 + 30 * 60,
                        "realtimeState": "SCHEDULED",
                    },
                    {
                        "serviceDay": service_day,
                            "scheduledDeparture": 6 * 3600 + 5 * 60,
                            "realtimeDeparture": 6 * 3600 + 5 * 60,
                        "realtimeState": "CANCELED",
                    },
                    {
                        "serviceDay": service_day,
                            "scheduledDeparture": 6 * 3600 + 10 * 60,
                            "realtimeDeparture": 6 * 3600 + 12 * 60,
                        "realtimeState": "UPDATED",
                    },
                ],
            }
        ],
        minimum_departure=minimum_departure,
        number_of_departures=4,
    )

    assert len(departures) == 1
    assert departures[0].route_short_name == "550"
    assert departures[0].delay_minutes == 2


def test_normalize_alerts_filters_by_effective_window() -> None:
    coordinator = _coordinator_instance()
    now = datetime.now(UTC)

    alerts = coordinator._normalize_alerts(
        [
            {
                "alertSeverityLevel": "INFO",
                "alertHeaderText": "Active alert",
                "alertHeaderTextTranslations": [{"language": "fi", "text": "Aktiivinen"}],
                "effectiveStartDate": (now - timedelta(minutes=10)).isoformat(),
                "effectiveEndDate": (now + timedelta(minutes=10)).isoformat(),
            },
            {
                "alertSeverityLevel": "INFO",
                "alertHeaderText": "Future alert",
                "effectiveStartDate": (now + timedelta(minutes=30)).isoformat(),
                "effectiveEndDate": None,
            },
            {
                "alertSeverityLevel": "INFO",
                "alertHeaderText": "Expired alert",
                "effectiveStartDate": None,
                "effectiveEndDate": (now - timedelta(minutes=1)).isoformat(),
            },
        ]
    )

    assert len(alerts) == 1
    assert alerts[0].header == "Active alert"
    assert alerts[0].translations == {"fi": "Aktiivinen"}


def test_normalize_stops_adds_missing_configured_stop() -> None:
    coordinator = _coordinator_instance()

    normalized = coordinator._normalize_stops(
        stops=[
            {
                "gtfsId": "HSL:1040273",
                "name": "Helsinki Main",
                "code": "H1243",
                "alerts": [],
                "stoptimesForPatterns": [],
            }
        ],
        configured_stop_ids=["HSL:1040273", "HSL:1041402"],
        number_of_departures=4,
        cutoff_minutes=0,
    )

    assert "HSL:1040273" in normalized
    assert "HSL:1041402" in normalized
    assert normalized["HSL:1040273"].stop_code == "H1243"
    assert normalized["HSL:1041402"].stop_code is None
    assert normalized["HSL:1041402"].departures == ()
    assert normalized["HSL:1041402"].alerts == ()


@pytest.mark.asyncio
async def test_async_update_data_reuses_cache_when_refresh_not_due() -> None:
    coordinator = _coordinator_instance()
    coordinator.entry = _build_entry()
    coordinator.api = AsyncMock()
    coordinator._cached_stops = [
        {
            "gtfsId": "HSL:1040273",
            "name": "Helsinki Main",
            "alerts": [],
            "stoptimesForPatterns": [],
        }
    ]
    coordinator._last_api_refresh = datetime.now(UTC)

    result = await coordinator._async_update_data()

    coordinator.api.async_get_departures.assert_not_called()
    assert "HSL:1040273" in result


@pytest.mark.asyncio
async def test_async_update_data_uses_cache_on_api_error() -> None:
    coordinator = _coordinator_instance()
    coordinator.entry = _build_entry()
    coordinator.api = AsyncMock()
    coordinator.api.async_get_departures.side_effect = TransitApiError("boom")
    coordinator._cached_stops = [
        {
            "gtfsId": "HSL:1040273",
            "name": "Helsinki Main",
            "alerts": [],
            "stoptimesForPatterns": [],
        }
    ]
    coordinator._last_api_refresh = datetime.now(UTC) - timedelta(minutes=30)

    result = await coordinator._async_update_data()

    coordinator.api.async_get_departures.assert_awaited_once()
    assert "HSL:1040273" in result


@pytest.mark.asyncio
async def test_async_update_data_raises_update_failed_when_no_cache() -> None:
    coordinator = _coordinator_instance()
    coordinator.entry = _build_entry()
    coordinator.api = AsyncMock()
    coordinator.api.async_get_departures.side_effect = TransitApiError("boom")
    coordinator._cached_stops = None
    coordinator._last_api_refresh = None

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()
