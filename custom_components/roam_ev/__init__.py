"""ROAM EV Charging integration for Home Assistant."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import RoamEVApi
from .const import (
    CONF_ID_TOKEN,
    CONF_REFRESH_TOKEN,
    CONF_USER_ID,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .coordinator import RoamEVCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ROAM EV Charging from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    session = async_get_clientsession(hass)

    # Create API client
    api = RoamEVApi(
        session,
        entry.data.get(CONF_EMAIL),
        entry.data.get(CONF_PASSWORD),
    )

    # Try to use stored tokens first
    if entry.data.get(CONF_ID_TOKEN) and entry.data.get(CONF_REFRESH_TOKEN):
        api.set_tokens(
            id_token=entry.data[CONF_ID_TOKEN],
            refresh_token=entry.data[CONF_REFRESH_TOKEN],
            user_id=entry.data[CONF_USER_ID],
        )

    # Create coordinator
    coordinator = RoamEVCoordinator(hass, api)

    # Update interval from options
    scan_interval = entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL)
    coordinator.update_interval = timedelta(seconds=scan_interval)

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Update stored tokens if they changed
    if api.refresh_token and api.refresh_token != entry.data.get(CONF_REFRESH_TOKEN):
        hass.config_entries.async_update_entry(
            entry,
            data={
                **entry.data,
                CONF_REFRESH_TOKEN: api.refresh_token,
                CONF_ID_TOKEN: api.id_token,
                CONF_USER_ID: api.user_id,
            },
        )

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register options update listener
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    _LOGGER.debug("Migrating from version %s", entry.version)

    if entry.version == 1:
        # No migration needed for version 1
        pass

    return True

