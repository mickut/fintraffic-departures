from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_ALERTS,
    ATTR_NEXT_DEPARTURES,
    ATTR_PRIMARY_DEPARTURE,
    ATTR_STOP_ID,
    ATTR_STOP_NAME,
    CONF_STOP_ID,
    DOMAIN,
    SUBENTRY_TYPE_STOP,
)
from .coordinator import TransitDeparturesCoordinator
from .models import StopData


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator: TransitDeparturesCoordinator = hass.data[DOMAIN][entry.entry_id]

    for subentry_id, subentry in entry.subentries.items():
        if subentry.subentry_type != SUBENTRY_TYPE_STOP:
            continue
        async_add_entities(
            [TransitDepartureSensor(coordinator, entry, subentry)],
            config_subentry_id=subentry_id,
        )


class TransitDepartureSensor(CoordinatorEntity[TransitDeparturesCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(
        self,
        coordinator: TransitDeparturesCoordinator,
        entry: ConfigEntry,
        subentry: ConfigSubentry,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._subentry = subentry
        self._stop_id = subentry.data[CONF_STOP_ID]
        self._attr_unique_id = f"{entry.entry_id}_{subentry.subentry_id}"

    @property
    def name(self) -> str:
        return f"{self._stop_data.stop_name} Next Departure"

    @property
    def available(self) -> bool:
        return super().available and self._stop_data is not None and bool(self._stop_data.departures)

    @property
    def native_value(self):
        if not self._stop_data.departures:
            return None
        return self._stop_data.departures[0].departure_datetime

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        primary = self._stop_data.departures[0].as_dict() if self._stop_data.departures else None
        next_departures = [departure.as_dict() for departure in self._stop_data.departures[1:]]
        alerts = [alert.as_dict() for alert in self._stop_data.alerts]

        return {
            ATTR_STOP_ID: self._stop_data.stop_id,
            ATTR_STOP_NAME: self._stop_data.stop_name,
            ATTR_PRIMARY_DEPARTURE: primary,
            ATTR_NEXT_DEPARTURES: next_departures,
            ATTR_ALERTS: alerts,
        }

    @property
    def _stop_data(self) -> StopData:
        return self.coordinator.data.get(
            self._stop_id,
            StopData(
                stop_id=self._stop_id,
                stop_name=self._stop_id,
                departures=(),
                alerts=(),
            ),
        )