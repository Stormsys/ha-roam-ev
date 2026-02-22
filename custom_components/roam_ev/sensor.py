"""Sensor platform for ROAM EV Charging."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, UnitOfEnergy, UnitOfPower, UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import SessionData
from .const import DOMAIN
from .coordinator import RoamEVCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class RoamEVSensorEntityDescription(SensorEntityDescription):
    """Describes ROAM EV sensor entity."""

    value_fn: Callable[[SessionData], Any]
    available_fn: Callable[[SessionData], bool] = lambda data: data.is_active


SENSOR_DESCRIPTIONS: tuple[RoamEVSensorEntityDescription, ...] = (
    RoamEVSensorEntityDescription(
        key="power",
        translation_key="power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.power if data.power else None,
    ),
    RoamEVSensorEntityDescription(
        key="energy",
        translation_key="energy",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.energy if data.energy else None,
    ),
    RoamEVSensorEntityDescription(
        key="charger_id",
        translation_key="charger_id",
        icon="mdi:ev-station",
        value_fn=lambda data: data.charger_id or data.evse_id,
    ),
    RoamEVSensorEntityDescription(
        key="transaction_id",
        translation_key="transaction_id",
        icon="mdi:identifier",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.transaction_id,
    ),
    RoamEVSensorEntityDescription(
        key="session_start",
        translation_key="session_start",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:clock-start",
        value_fn=lambda data: _parse_timestamp(data.started_charging_at),
    ),
    RoamEVSensorEntityDescription(
        key="session_status",
        translation_key="session_status",
        icon="mdi:information",
        value_fn=lambda data: _status_to_string(data.status),
        available_fn=lambda data: True,  # Always available
    ),
    RoamEVSensorEntityDescription(
        key="session_cost",
        translation_key="session_cost",
        icon="mdi:currency-gbp",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="GBP",
        suggested_display_precision=2,
        value_fn=lambda data: data.session_cost,
    ),
    RoamEVSensorEntityDescription(
        key="evse_id",
        translation_key="evse_id",
        icon="mdi:ev-plug-type2",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.evse_id,
    ),
    RoamEVSensorEntityDescription(
        key="qr_code",
        translation_key="qr_code",
        icon="mdi:qrcode",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.qr_code,
    ),
    RoamEVSensorEntityDescription(
        key="manual_input_code",
        translation_key="manual_input_code",
        icon="mdi:form-textbox-password",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.manual_input_code,
    ),
    RoamEVSensorEntityDescription(
        key="tariff_rate",
        translation_key="tariff_rate",
        icon="mdi:cash",
        native_unit_of_measurement="GBP/kWh",
        suggested_display_precision=2,
        value_fn=lambda data: data.numeric_rate,
    ),
    RoamEVSensorEntityDescription(
        key="session_updated_at",
        translation_key="session_updated_at",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:clock-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: _parse_timestamp(data.updated_at),
    ),
    RoamEVSensorEntityDescription(
        key="energy_updated_at",
        translation_key="energy_updated_at",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:clock-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: _parse_timestamp(data.energy_updated_at),
    ),
    RoamEVSensorEntityDescription(
        key="charger_name",
        translation_key="charger_name",
        icon="mdi:ev-station",
        value_fn=lambda data: data.charger_name or data.charger_id or data.evse_id,
    ),
    RoamEVSensorEntityDescription(
        key="charger_location",
        translation_key="charger_location",
        icon="mdi:map-marker",
        value_fn=lambda data: data.charger_location,
    ),
    RoamEVSensorEntityDescription(
        key="connector_type",
        translation_key="connector_type",
        icon="mdi:ev-plug-type2",
        value_fn=lambda data: data.connector_type,
    ),
    RoamEVSensorEntityDescription(
        key="max_power",
        translation_key="max_power",
        icon="mdi:flash",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        value_fn=lambda data: data.max_power,
    ),
    RoamEVSensorEntityDescription(
        key="session_duration",
        translation_key="session_duration",
        icon="mdi:timer-outline",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        suggested_display_precision=0,
        value_fn=lambda data: _session_duration_seconds(data.started_charging_at),
    ),
)


def _parse_timestamp(timestamp_str: str | None) -> datetime | None:
    """Parse a timestamp string to datetime."""
    if not timestamp_str:
        return None
    try:
        # Firebase timestamps are ISO format
        return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _session_duration_seconds(started_at: str | None) -> int | None:
    """Calculate session duration in seconds from start timestamp."""
    if not started_at:
        return None
    start = _parse_timestamp(started_at)
    if start is None:
        return None
    from datetime import timezone

    now = datetime.now(timezone.utc)
    delta = now - start
    return max(0, int(delta.total_seconds()))


def _status_to_string(status: int | None) -> str:
    """Convert status code to human-readable string."""
    if status is None or status == 0:
        return "idle"
    if status == 1:
        return "preparing"
    if status == 2:
        return "charging"
    if status == 3:
        return "finishing"
    if status == 4:
        return "completed"
    if status == 5:
        return "error"
    return f"unknown ({status})"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ROAM EV sensors."""
    coordinator: RoamEVCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = [
        RoamEVSensor(coordinator, entry, description)
        for description in SENSOR_DESCRIPTIONS
    ]
    entities.append(RoamEVLastSessionCostSensor(coordinator, entry))

    async_add_entities(entities)


class RoamEVSensor(CoordinatorEntity[RoamEVCoordinator], SensorEntity):
    """Sensor for ROAM EV charging data."""

    _attr_has_entity_name = True
    entity_description: RoamEVSensorEntityDescription

    def __init__(
        self,
        coordinator: RoamEVCoordinator,
        entry: ConfigEntry,
        description: RoamEVSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"

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
    def available(self) -> bool:
        """Return if entity is available."""
        if not super().available or self.coordinator.data is None:
            return False
        return self.entity_description.available_fn(self.coordinator.data)

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)


class RoamEVLastSessionCostSensor(CoordinatorEntity[RoamEVCoordinator], SensorEntity):
    """Sensor for the cost of the last completed charging session."""

    _attr_has_entity_name = True
    _attr_translation_key = "last_session_cost"
    _attr_icon = "mdi:currency-gbp"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "GBP"
    _attr_suggested_display_precision = 2

    def __init__(
        self,
        coordinator: RoamEVCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_last_session_cost"

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
    def native_value(self) -> float | None:
        """Return the cost of the last session."""
        return self.coordinator.last_session_cost

