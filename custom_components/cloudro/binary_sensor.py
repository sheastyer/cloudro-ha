"""Binary sensor platform for the Cloud RO integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .cloudro_ble import CloudROState

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import CloudROConfigEntry, CloudRODataUpdateCoordinator
from .entity import CloudROEntity


@dataclass(frozen=True, kw_only=True)
class CloudROBinarySensorDescription(BinarySensorEntityDescription):
    """Describes a Cloud RO binary sensor."""

    value_fn: Callable[[CloudROState], bool]


BINARY_SENSORS: tuple[CloudROBinarySensorDescription, ...] = (
    CloudROBinarySensorDescription(
        key="problem",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.measured.error_code != 0,
    ),
    CloudROBinarySensorDescription(
        key="flow",
        translation_key="flow",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda s: s.measured.flow != 0,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CloudROConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Cloud RO binary sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        CloudROBinarySensor(coordinator, description)
        for description in BINARY_SENSORS
    )


class CloudROBinarySensor(CloudROEntity, BinarySensorEntity):
    """A single Cloud RO binary sensor."""

    entity_description: CloudROBinarySensorDescription

    def __init__(
        self,
        coordinator: CloudRODataUpdateCoordinator,
        description: CloudROBinarySensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.address}_{description.key}"

    @property
    def is_on(self) -> bool:
        return self.entity_description.value_fn(self.coordinator.data)
