from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from custom_components.transit_departures.sensor import TransitDepartureSensor
from custom_components.transit_departures.models import AlertInfo, DepartureInfo, StopData


class _DummyCoordinator:
    def __init__(self, data: dict[str, StopData]) -> None:
        self.data = data
        self.last_update_success = True


def test_sensor_native_value_and_attributes() -> None:
    departure_1 = DepartureInfo(
        stop_id="HSL:1040273",
        stop_name="Helsinki Main",
        pattern_code="550",
        headsign="Itakeskus",
        route_short_name="550",
        route_long_name="Jokeri",
        scheduled_datetime=datetime(2026, 5, 22, 8, 0, tzinfo=UTC),
        departure_datetime=datetime(2026, 5, 22, 8, 2, tzinfo=UTC),
        realtime_state="UPDATED",
        delay_minutes=2,
    )
    departure_2 = DepartureInfo(
        stop_id="HSL:1040273",
        stop_name="Helsinki Main",
        pattern_code="550",
        headsign="Itakeskus",
        route_short_name="550",
        route_long_name="Jokeri",
        scheduled_datetime=datetime(2026, 5, 22, 8, 10, tzinfo=UTC),
        departure_datetime=datetime(2026, 5, 22, 8, 10, tzinfo=UTC),
        realtime_state="SCHEDULED",
        delay_minutes=0,
    )
    alert = AlertInfo(
        severity="INFO",
        header="Minor delay",
        translations={"fi": "Pieni viive"},
        effective_start=datetime(2026, 5, 22, 7, 0, tzinfo=UTC),
        effective_end=datetime(2026, 5, 22, 12, 0, tzinfo=UTC),
    )

    stop_data = StopData(
        stop_id="HSL:1040273",
        stop_name="Helsinki Main",
        stop_code="H1243",
        departures=(departure_1, departure_2),
        alerts=(alert,),
    )

    coordinator = _DummyCoordinator({"HSL:1040273": stop_data})
    entry = SimpleNamespace(
        entry_id="entry-1",
        data={"prefix": "", "suffix": "Next Departure"},
        options={},
    )
    subentry = SimpleNamespace(subentry_id="sub-1", data={"stop_id": "HSL:1040273"})

    sensor = TransitDepartureSensor(coordinator, entry, subentry)

    assert sensor.name == "Helsinki Main H1243 Next Departure"
    assert sensor.native_value == departure_1.departure_datetime
    attrs = sensor.extra_state_attributes
    assert attrs["stop_id"] == "HSL:1040273"
    assert attrs["stop_code"] == "H1243"
    assert attrs["primary_departure"]["route_label"] == "550"
    assert len(attrs["next_departures"]) == 1
    assert attrs["alerts"][0]["header"] == "Minor delay"


def test_sensor_returns_none_without_departures() -> None:
    stop_data = StopData(
        stop_id="HSL:1041402",
        stop_name="Kamppi",
        stop_code=None,
        departures=(),
        alerts=(),
    )

    coordinator = _DummyCoordinator({"HSL:1041402": stop_data})
    entry = SimpleNamespace(
        entry_id="entry-1",
        data={"prefix": "", "suffix": "Next Departure"},
        options={},
    )
    subentry = SimpleNamespace(subentry_id="sub-2", data={"stop_id": "HSL:1041402"})

    sensor = TransitDepartureSensor(coordinator, entry, subentry)

    assert sensor.name == "Kamppi Next Departure"
    assert sensor.native_value is None
    assert sensor.extra_state_attributes["stop_code"] is None
    assert sensor.extra_state_attributes["primary_departure"] is None


def test_sensor_name_uses_custom_and_disabled_suffix_rules() -> None:
    stop_data = StopData(
        stop_id="HSL:1040273",
        stop_name="Helsinki Main",
        stop_code="H1243",
        departures=(),
        alerts=(),
    )
    coordinator = _DummyCoordinator({"HSL:1040273": stop_data})
    entry = SimpleNamespace(
        entry_id="entry-1",
        data={"prefix": "", "suffix": "Next Departure"},
        options={"prefix": "Bus", "suffix": "Next Departure"},
    )

    custom_subentry = SimpleNamespace(
        subentry_id="sub-1",
        data={"stop_id": "HSL:1040273", "stop_suffix": "Gate A"},
    )
    custom_sensor = TransitDepartureSensor(coordinator, entry, custom_subentry)
    assert custom_sensor.name == "Bus Helsinki Main Gate A Next Departure"
    assert custom_sensor.extra_state_attributes["stop_code"] == "Gate A"

    disabled_subentry = SimpleNamespace(
        subentry_id="sub-2",
        data={"stop_id": "HSL:1040273", "disable_stop_suffix": True},
    )
    disabled_sensor = TransitDepartureSensor(coordinator, entry, disabled_subentry)
    assert disabled_sensor.name == "Bus Helsinki Main Next Departure"
    assert disabled_sensor.extra_state_attributes["stop_code"] == "H1243"
