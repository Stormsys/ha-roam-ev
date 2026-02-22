"""Binary sensor platform for ROAM EV Charging."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import RoamEVCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ROAM EV binary sensors."""
    coordinator: RoamEVCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([RoamEVChargingSessionSensor(coordinator, entry)])


class RoamEVChargingSessionSensor(CoordinatorEntity[RoamEVCoordinator], BinarySensorEntity):
    """Binary sensor for active charging session."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.BATTERY_CHARGING
    _attr_translation_key = "charging_session"

    def __init__(
        self,
        coordinator: RoamEVCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_charging_session"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=f"ROAM EV ({self._entry.data.get(CONF_EMAIL, 'Account')})",
            manufacturer="ROAM EV",
            model="EV Charging Account",
        )

    @property
    def is_on(self) -> bool:
        """Return true if charging session is active."""
        if self.coordinator.data is None:
            return False
        return self.coordinator.data.is_active

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        if self.coordinator.data is None or not self.coordinator.data.is_active:
            return {}

        data = self.coordinator.data
        attrs = {}

        if data.charger_id:
            attrs["charger_id"] = data.charger_id
        if data.evse_id:
            attrs["evse_id"] = data.evse_id
        if data.transaction_id:
            attrs["transaction_id"] = data.transaction_id
        if data.status is not None:
            attrs["status"] = data.status
        if data.started_charging_at:
            attrs["started_at"] = data.started_charging_at
        if data.power:
            attrs["power_w"] = data.power
        if data.energy:
            attrs["energy_wh"] = data.energy

        return attrs

