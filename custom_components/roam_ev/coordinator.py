"""Data coordinator for ROAM EV Charging."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ConfigEntryAuthFailed

from .api import RoamEVApi, RoamEVApiError, RoamEVAuthError, SessionData
from .const import (
    CONF_ID_TOKEN,
    CONF_REFRESH_TOKEN,
    CONF_USER_ID,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class RoamEVCoordinator(DataUpdateCoordinator[SessionData]):
    """Coordinator for ROAM EV data updates."""

    def __init__(
        self, hass: HomeAssistant, api: RoamEVApi, entry: ConfigEntry
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.api = api
        self._entry = entry
        self._charger_cache: dict[str, Any] = {}
        self._last_saved_refresh_token: str | None = entry.data.get(CONF_REFRESH_TOKEN)

    async def _async_update_data(self) -> SessionData:
        """Fetch data from API."""
        try:
            session_data = await self.api.get_session_data()

            # If session is active and we have a charger ID, fetch charger details
            if session_data.is_active:
                charger_id = session_data.charger_id or session_data.evse_id
                if charger_id and charger_id not in self._charger_cache:
                    charger_details = await self.api.get_charger_details(charger_id)
                    if charger_details:
                        self._charger_cache[charger_id] = charger_details

            # Persist tokens if they changed after a refresh/re-auth
            self._persist_tokens_if_changed()

            return session_data

        except RoamEVAuthError as err:
            # Authentication error - trigger reauthentication flow
            raise ConfigEntryAuthFailed(f"Authentication failed: {err}") from err

        except RoamEVApiError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    def _persist_tokens_if_changed(self) -> None:
        """Save updated tokens to config entry if they changed."""
        if (
            self.api.refresh_token
            and self.api.refresh_token != self._last_saved_refresh_token
        ):
            _LOGGER.debug("Persisting updated tokens to config entry")
            self._last_saved_refresh_token = self.api.refresh_token
            self.hass.config_entries.async_update_entry(
                self._entry,
                data={
                    **self._entry.data,
                    CONF_REFRESH_TOKEN: self.api.refresh_token,
                    CONF_ID_TOKEN: self.api.id_token,
                    CONF_USER_ID: self.api.user_id,
                },
            )

    def get_charger_info(self, charger_id: str) -> dict[str, Any] | None:
        """Get cached charger information."""
        return self._charger_cache.get(charger_id)

