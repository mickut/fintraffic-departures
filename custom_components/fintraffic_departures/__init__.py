from __future__ import annotations

import logging
from types import MappingProxyType

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import CONF_STOP_ID, DOMAIN, SUBENTRY_TYPE_STOP, normalize_stop_id
from .coordinator import FintrafficDeparturesCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]
LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = FintrafficDeparturesCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    entry.async_on_unload(entry.add_update_listener(async_update_entry))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_update_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry when shared settings or subentries change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate legacy stop_ids data to stop subentries."""
    LOGGER.debug("Migrating config entry from version %s.%s", entry.version, entry.minor_version)

    if entry.version > 1 or (entry.version == 1 and entry.minor_version > 2):
        return False

    if entry.version == 1 and entry.minor_version < 2:
        old_stop_ids = entry.data.get("stop_ids", [])
        old_to_new_subentry_id: dict[str, str] = {}

        if isinstance(old_stop_ids, list):
            for old_stop_id in old_stop_ids:
                if not isinstance(old_stop_id, str):
                    continue

                raw_stop_id = old_stop_id.strip()
                normalized_stop_id = normalize_stop_id(old_stop_id)
                subentry = ConfigSubentry(
                    data=MappingProxyType({CONF_STOP_ID: normalized_stop_id}),
                    subentry_type=SUBENTRY_TYPE_STOP,
                    title=normalized_stop_id,
                    unique_id=normalized_stop_id,
                )
                old_to_new_subentry_id[f"{entry.entry_id}_{raw_stop_id}"] = subentry.subentry_id
                old_to_new_subentry_id[f"{entry.entry_id}_{normalized_stop_id}"] = subentry.subentry_id
                hass.config_entries.async_add_subentry(entry, subentry)

        entity_reg = er.async_get(hass)
        for entity in er.async_entries_for_config_entry(entity_reg, entry.entry_id):
            if entity.unique_id not in old_to_new_subentry_id:
                continue

            subentry_id = old_to_new_subentry_id[entity.unique_id]
            entity_reg.async_update_entity(
                entity.entity_id,
                config_entry_id=entry.entry_id,
                config_subentry_id=subentry_id,
                new_unique_id=f"{entry.entry_id}_{subentry_id}",
            )

        new_data = dict(entry.data)
        new_data.pop("stop_ids", None)
        hass.config_entries.async_update_entry(entry, data=new_data, minor_version=2)

    return True