"""Sensor platform for the Cloud RO integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .cloudro_ble import CloudROState

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfElectricPotential,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import CloudROConfigEntry, CloudRODataUpdateCoordinator
from .entity import CloudROEntity

PPM = "ppm"


@dataclass(frozen=True, kw_only=True)
class CloudROSensorDescription(SensorEntityDescription):
    """Describes a Cloud RO sensor and how to read it from device state."""

    value_fn: Callable[[CloudROState], float | int | None]


SENSORS: tuple[CloudROSensorDescription, ...] = (
    CloudROSensorDescription(
        key="inlet_tds",
        translation_key="inlet_tds",
        native_unit_of_measurement=PPM,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.measured.inlet_tds,
    ),
    CloudROSensorDescription(
        key="post_ro_tds",
        translation_key="post_ro_tds",
        native_unit_of_measurement=PPM,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.measured.post_ro_tds,
    ),
    CloudROSensorDescription(
        key="remin_tds",
        translation_key="remin_tds",
        native_unit_of_measurement=PPM,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.measured.remin_tds,
    ),
    CloudROSensorDescription(
        key="tank_fill",
        translation_key="tank_fill",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda s: s.measured.tank_fill_percent,
    ),
    CloudROSensorDescription(
        key="total_dispensed",
        translation_key="total_dispensed",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda s: s.measured.total_dispensed_water,
    ),
    CloudROSensorDescription(
        key="battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.measured.battery_life,
    ),
    CloudROSensorDescription(
        key="battery_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
        value_fn=lambda s: s.measured.battery_voltage,
    ),
    CloudROSensorDescription(
        key="tank_pressure",
        translation_key="tank_pressure",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda s: s.measured.tank_pressure,
    ),
    CloudROSensorDescription(
        key="stored_water_raw",
        translation_key="stored_water_raw",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda s: s.measured.stored_water,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CloudROConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Cloud RO sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        CloudROSensor(coordinator, description) for description in SENSORS
    )


class CloudROSensor(CloudROEntity, SensorEntity):
    """A single Cloud RO sensor."""

    entity_description: CloudROSensorDescription

    def __init__(
        self,
        coordinator: CloudRODataUpdateCoordinator,
        description: CloudROSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.address}_{description.key}"

    @property
    def native_value(self) -> float | int | None:
        return self.entity_description.value_fn(self.coordinator.data)
